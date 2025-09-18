import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import io

# ✅ Page config (must be the first Streamlit call)
st.set_page_config(page_title="Keogh/401(k) Projection", layout="wide")

# ── Title and icon ────────────────────────────────────────────────────────────
img_col, title_col = st.columns([0.15, 0.85])
with img_col:
    # If you want to use Image_3.png instead, just change the file name here
    st.image("Image_2.png", use_container_width=True)
with title_col:
    st.title("Future Value Calculator for Keogh/401(k)")

# ── Sidebar: Theme + Inputs ───────────────────────────────────────────────────
st.sidebar.title("Display & Inputs")

# Theme toggle (projector aware)
theme = st.sidebar.radio(
    "Theme",
    options=["Light (projector-friendly default)", "Dark (high-contrast)"],
    index=0,
    help="Light uses off-white backgrounds to reduce glare on projectors. Dark uses deep gray with bright accents.",
    key="theme_mode",
)

# Color scheme presets
color_schemes = {
    # Original sets
    "Blues": ("#377eb8", "#4daf4a"),
    "Grays": ("#999999", "#666666"),
    "Red & Blue": ("#e41a1c", "#377eb8"),
    "Purples": ("#984ea3", "#7570b3"),
    "Orange & Teal": ("#ff7f00", "#1b9e77"),
    # Projector-optimized sets
    "Blue & Orange (good for projectors)": ("#377eb8", "#ff7f00"),
    "Teal & Purple (good for projectors)": ("#1b9e77", "#984ea3"),
    "Blue & Gray (good for projectors)": ("#377eb8", "#666666"),
}
selected_scheme = st.sidebar.selectbox(
    "Select Color Scheme",
    list(color_schemes.keys()),
    key="color_scheme",
)
contrib_color, earnings_color = color_schemes[selected_scheme]
starting_color = "#d1d5db" if "Light" in theme else "#4b5563"  # band for Starting Savings

# ── 401(k) inputs ────────────────────────────────────────────────────────────
st.sidebar.subheader("401(k) Inputs")

# NEW: Optional current savings (ADDED AT YEAR 0)
current_savings = st.sidebar.number_input(
    "Current Savings (optional — added at Year 0)",
    min_value=0.0, max_value=10_000_000.0,
    value=0.0, step=1_000.0,
    key="current_savings",
    help="If you enter a value here, set Initial Start Age to your CURRENT age so Year 0 represents today."
)

# Optional second schedule (default ON)
use_second = st.sidebar.checkbox(
    "Use second contribution schedule",
    value=True,
    help="If unchecked, only the initial contribution is used throughout.",
    key="use_second",
)

# 🔹 NEW: Contribution Mode Toggle (Fixed Dollar vs Percent of Salary)
contrib_mode = st.sidebar.radio(
    "Contribution Mode",
    options=["Fixed Dollar Amount", "Percent of Salary"],
    index=0,
    help="Choose whether your contribution is a fixed annual $ amount or a % of salary.",
    key="contrib_mode"
)

# Existing fixed-dollar inputs (kept exactly as-is)
init_contrib = st.sidebar.number_input(
    "Initial contribution amount (annual)", 1000, 1_000_000, 50_000, 1_000, key="init_contrib"
)
init_age = st.sidebar.number_input("Initial Start Age", 18, 80, 35, 1, key="init_age")

second_contrib = st.sidebar.number_input(
    "Second contribution amount (annual)", 1000, 1_000_000, 55_000, 1_000, key="second_contrib"
)
second_age_default = max(50, int(init_age))
second_age = st.sidebar.number_input("Second Start Age", int(init_age), 80, second_age_default, 1, key="second_age")

# 🔹 NEW: Percent-of-salary inputs (shown when mode is Percent of Salary)
if contrib_mode == "Percent of Salary":
    base_salary = st.sidebar.number_input(
        "Current Salary",
        min_value=10_000.0, max_value=1_000_000.0, value=120_000.0, step=1_000.0,
        help="Used to compute contribution when in Percent of Salary mode.",
        key="base_salary"
    )
    init_percent = st.sidebar.slider(
        "Employee Contribution % (initial)",
        0.0, 100.0, 10.0, 0.5, key="init_percent_pct"
    )
    second_percent = st.sidebar.slider(
        "Employee Contribution % (second schedule)",
        0.0, 100.0, 12.0, 0.5, key="second_percent_pct"
    )
    annual_raise = st.sidebar.slider(
        "Annual Pay Increase %",
        0.0, 10.0, 3.0, 0.1,
        help="Applied to salary at the start of each plan year after Year 0.",
        key="annual_raise_pct"
    )
else:
    # Defaults when using Fixed Dollar Amount mode (no salary logic)
    base_salary = 0.0
    init_percent = None
    second_percent = None
    annual_raise = 0.0

# RENAMED: Employer match → Employer contribution
employer_contrib_rate = st.sidebar.number_input(
    "Employer contribution % (0.00–1.00)", 0.0, 1.0, 0.0, 0.01, key="employer_contrib_rate"
)
annual_return = st.sidebar.number_input(
    "Annual Return Rate (0.00–0.20)", 0.0, 0.20, 0.06, 0.01, key="annual_return"
)
ret_age = st.sidebar.number_input(
    "Retirement Age",
    min_value=int(init_age) + 1,
    max_value=100,
    value=max(65, int(init_age) + 1),
    step=1,
    key="ret_age",
)
frequency = st.sidebar.selectbox(
    "Compounding Frequency", ["biweekly", "monthly", "quarterly"], key="comp_freq"
)
periods_per_year = {"biweekly": 26, "monthly": 12, "quarterly": 4}[frequency]
rate_per_period = (1 + annual_return) ** (1 / periods_per_year) - 1

# 🔹 NEW: IRS elective deferral limit controls (+ custom physician limit)
st.sidebar.markdown("---")
apply_irs_limit = st.sidebar.checkbox(
    "Apply IRS Elective Deferral Limit (cap employee contributions)",
    value=True,
    help="Caps employee contributions each year; employer contributions are not capped.",
    key="apply_irs_limit"
)
custom_physician_limit = st.sidebar.checkbox(
    "Use Custom Physician Limit Instead",
    value=True,
    help="Overrides IRS limit with a custom annual cap (e.g., for physicians).",
    key="custom_phys_limit"
)
custom_limit_amount = 70000.0
if custom_physician_limit and apply_irs_limit:
    custom_limit_amount = st.sidebar.number_input(
        "Custom Annual Limit ($)",
        min_value=10_000.0, max_value=500_000.0,
        value=70_000.0, step=1_000.0,
        key="custom_limit_amount"
    )

with st.sidebar.expander("IRS Limit Settings"):
    col1, col2 = st.columns(2)
    base_year = int(col1.number_input("Base Year", 2000, 2100, 2024, 1, key="irs_base_year"))
    inflation_rate = float(col2.number_input("Inflation %/yr", 0.0, 10.0, 0.0, 0.1, key="irs_inflation"))
    col3, col4 = st.columns(2)
    base_limit = float(col3.number_input("Base Limit ($)", 0.0, 200_000.0, 23_000.0, 500.0, key="irs_base_limit"))
    catchup_limit = float(col4.number_input("Catch-up ($, 50+)", 0.0, 100_000.0, 7_500.0, 500.0, key="irs_catchup"))

# Gentle reminder if user entered starting savings
if current_savings > 0:
    st.info(
        "You entered **Current Savings**. Please ensure **Initial Start Age** equals your **current age** "
        "so Year 0 represents **today** and includes your starting balance."
    )

# Guardrail: Second Start Age must be >= Initial Start Age when enabled
if use_second and second_age < init_age:
    st.error("Second Start Age cannot be before Initial Start Age. Please adjust in the sidebar.")
    st.stop()

# ── Matplotlib theme helpers (projector-aware) ────────────────────────────────
def mpl_palette(theme_name: str):
    if "Dark" in theme_name:
        return {
            "fig_bg": "#111418",
            "ax_bg": "#0c0f13",
            "grid": "#3c4043",
            "text": "#e8eaed",
            "spine": "#8b949e",
            "annot_fc": "#1b1f24",
            "annot_ec": "#333333",
        }
    # Light (projector-friendly): off-white figure with white axes for contrast
    return {
        "fig_bg": "#f7f7f7",
        "ax_bg": "#ffffff",
        "grid": "#9aa0a6",
        "text": "#222222",
        "spine": "#666666",
        "annot_fc": "#ffffff",
        "annot_ec": "#cfcfcf",
    }

palette = mpl_palette(theme)

# Apply text/axis colors for readability *before* plotting
plt.rcParams.update({
    "axes.labelcolor": palette["text"],
    "text.color": palette["text"],
    "xtick.color": palette["text"],
    "ytick.color": palette["text"],
    "axes.titlecolor": palette["text"],
    "axes.edgecolor": palette["spine"],
})

# 🔹 NEW: IRS helper
def irs_limit(plan_year: int, age: int) -> float:
    """
    Returns the IRS elective deferral limit for a given plan year and age.
    Applies a simple compounded inflation adjustment from base_year if inflation_rate > 0.
    Includes catch-up only when age >= 50 during that year.
    """
    years_since_base = max(0, plan_year - base_year)
    limit = base_limit * ((1 + inflation_rate / 100.0) ** years_since_base)
    if age >= 50:
        limit += catchup_limit
    return float(limit)

# ── Projection calculation ────────────────────────────────────────────────────
years = int(ret_age - init_age)
total_periods = years * periods_per_year

balance = float(current_savings)  # start with current savings (added at Year 0)
cum_contrib = 0.0
cum_earnings = 0.0
annual_data = []

# 🔹 Percent-of-salary mode state
salary = float(base_salary) if contrib_mode == "Percent of Salary" else 0.0
employee_contrib_per_period = 0.0  # set at plan-year boundaries

for period in range(total_periods + 1):
    age = init_age + period / periods_per_year
    year_idx = int(age - init_age)
    is_year_start = (period % periods_per_year == 0)

    # 🔹 In Percent of Salary mode, apply annual raise at start of each new plan year (after Year 0)
    if contrib_mode == "Percent of Salary" and is_year_start and period > 0:
        salary *= (1 + (annual_raise / 100.0))

    # Choose contribution schedule (initial vs second) and compute EMPLOYEE annual amount
    if is_year_start:
        if contrib_mode == "Percent of Salary":
            pct = (second_percent if (use_second and age >= second_age) else init_percent) or 0.0
            employee_annual = salary * (pct / 100.0)
        else:
            # Original fixed-dollar behavior
            contrib_annual = init_contrib if (not use_second or age < second_age) else second_contrib
            employee_annual = float(contrib_annual)

        # 🔹 Apply contribution caps (employee portion only)
        if apply_irs_limit:
            if custom_physician_limit:
                employee_annual = min(employee_annual, float(custom_limit_amount))
            else:
                employee_annual = min(employee_annual, irs_limit(base_year + year_idx, int(age)))

        # Spread the employee amount across periods for this plan year
        employee_contrib_per_period = employee_annual / periods_per_year

    # Employer contribution based on this period's employee contribution
    employer_amt = employee_contrib_per_period * employer_contrib_rate
    total_contrib = employee_contrib_per_period + employer_amt

    # Earnings on current balance
    earnings = balance * rate_per_period

    # Update balance and cumulative components
    balance += total_contrib + earnings
    cum_contrib += total_contrib
    cum_earnings += earnings

    # capture at whole-year boundaries
    if is_year_start:
        annual_data.append({
            "Year": int(age - init_age),
            "Age": int(round(age)),
            "StartingSavings": float(current_savings),   # constant component for stacking/labeling
            "Contributions": cum_contrib,
            "Earnings": cum_earnings,
            "Total": balance
        })

df = pd.DataFrame(annual_data)
df = df[df["Year"] <= years]

# ── KPI Metrics ───────────────────────────────────────────────────────────────
end_balance = float(df["Total"].iloc[-1]) if not df.empty else 0.0
end_contrib = float(df["Contributions"].iloc[-1]) if not df.empty else 0.0
end_earnings = float(df["Earnings"].iloc[-1]) if not df.empty else 0.0

if current_savings > 0:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Ending Balance", f"${end_balance:,.0f}")
    col2.metric("📥 Contributions (incl. employer)", f"${end_contrib:,.0f}")
    col3.metric("📈 Earnings", f"${end_earnings:,.0f}")
    col4.metric("🏦 Starting Savings (Year 0)", f"${current_savings:,.0f}")
else:
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Ending Balance", f"${end_balance:,.0f}")
    col2.metric("📥 Contributions (incl. employer)", f"${end_contrib:,.0f}")
    col3.metric("📈 Earnings", f"${end_earnings:,.0f}")

# ── Chart (stacked, with optional Starting Savings band) ──────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor(palette["fig_bg"])
ax.set_facecolor(palette["ax_bg"])

bottoms = np.zeros(len(df))
if current_savings > 0:
    start_bars = ax.bar(
        df["Year"], df["StartingSavings"],
        color=starting_color, edgecolor="none", label="Starting Savings", zorder=1
    )
    bottoms = df["StartingSavings"].values

# Contributions stacked above starting savings
ax.bar(
    df["Year"], df["Contributions"],
    bottom=bottoms, color=contrib_color, edgecolor="none", label="Contributions", zorder=2
)

# Earnings stacked above both
ax.bar(
    df["Year"], df["Earnings"],
    bottom=bottoms + df["Contributions"], color=earnings_color, edgecolor="none", label="Earnings", zorder=3
)

# Labels and grid
ax.set_xlabel("Years Worked")
ax.set_ylabel("Amount ($)")
ax.set_title("Future Value Calculation", fontsize=11)
ax.legend(frameon=True)
ax.ticklabel_format(style='plain', axis='y')
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
ax.grid(axis='y', linestyle='--', alpha=0.6, color=palette["grid"])

# Headroom so callouts have space
max_total = float(df["Total"].max()) if not df.empty else 1.0
ymin, ymax = ax.get_ylim()
top_with_headroom = max_total * 1.28
if ymax < top_with_headroom:
    ax.set_ylim(top=top_with_headroom)

# Label the Year 0 Starting Savings inside the bar
if current_savings > 0:
    text_color = "#1f2937" if "Light" in theme else "#e5e7eb"  # readable gray
    labels = [f"Starting\n${current_savings:,.0f}"] + [""] * (len(df) - 1)
    ax.bar_label(ax.containers[0], labels=labels, label_type="center", fontsize=9, color=text_color)

# ── Non-overlapping milestone callouts ────────────────────────────────────────
def add_callouts_no_overlap(points, left_right_offsets=(-0.9, 0.9), y_gap_frac=0.06):
    """
    Stagger annotation boxes vertically to avoid overlap.
    points: list of dicts with keys {x, y, label}
    left_right_offsets: tuple of x offsets (in data units) alternated across points
    y_gap_frac: minimum vertical gap between boxes as a fraction of current ymax
    """
    if not points:
        return
    _ymin, _ymax = ax.get_ylim()
    gap = y_gap_frac * _ymax
    pts = sorted(points, key=lambda p: p["y"])
    last_yt = -np.inf
    for i, p in enumerate(pts):
        xoff = left_right_offsets[i % 2]
        base_yt = p["y"] * 1.10 if p["y"] > 0 else gap
        yt = max(base_yt, last_yt + gap)
        if yt > ax.get_ylim()[1] * 0.98:
            yt = ax.get_ylim()[1] * 0.98
        ax.annotate(
            p["label"],
            xy=(p["x"], p["y"]),
            xytext=(p["x"] + xoff, yt),
            textcoords="data",
            arrowprops=dict(facecolor="black", arrowstyle="->", lw=1),
            fontsize=9,
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.3", fc=palette["annot_fc"], ec=palette["annot_ec"])
        )
        last_yt = yt

def _age_to_xy(age_int: int):
    row = df.loc[df["Age"] == int(age_int)]
    if row.empty:
        return None, None
    return int(row["Year"].iloc[0]), float(row["Total"].iloc[0])

ann_points = []
# Initial Start
x0, y0 = _age_to_xy(int(init_age))
if x0 is not None:
    ann_points.append({"x": x0, "y": y0, "label": f"Initial Start\nAge: {int(init_age)}\nTotal: ${y0:,.0f}"})
# Second Start (optional)
if use_second:
    xs, ys = _age_to_xy(int(second_age))
    if xs is not None:
        ann_points.append({"x": xs, "y": ys, "label": f"Second Start\nAge: {int(second_age)}\nTotal: ${ys:,.0f}"})
# Retirement
xr, yr = _age_to_xy(int(ret_age))
if xr is not None:
    ann_points.append({"x": xr, "y": yr, "label": f"Retirement\nAge: {int(ret_age)}\nTotal: ${yr:,.0f}"})

add_callouts_no_overlap(ann_points)

plt.tight_layout()

# ── Export Chart (PNG) — button above the chart ───────────────────────────────
png_buf = io.BytesIO()
fig.savefig(png_buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight", dpi=200)
png_buf.seek(0)
st.download_button(
    "📷 Export Chart (PNG)",
    data=png_buf.getvalue(),
    file_name="keogh401k_chart.png",
    mime="image/png",
    key="download-chart-png",
)

# Render chart
st.pyplot(fig)

# Caption under chart
st.caption("Created by David Selevan")

# ── Export Table ──────────────────────────────────────────────────────────────
# Try Excel; if engine not present in runtime, fall back to CSV
try:
    import openpyxl  # noqa: F401
    xlsx_buf = io.BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Projection")
    xlsx_buf.seek(0)
    st.download_button(
        "📄 Export Table (Excel)",
        data=xlsx_buf.getvalue(),
        file_name="keogh401k_table.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download-table-xlsx",
    )
except Exception:
    csv_data = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📄 Export Table (CSV)",
        data=csv_data,
        file_name="keogh401k_table.csv",
        mime="text/csv",
        key="download-table-csv",
    )

# ── Data Table ────────────────────────────────────────────────────────────────
view_cols = ["Year", "Age"] + (["StartingSavings"] if current_savings > 0 else []) + ["Contributions", "Earnings", "Total"]
st.dataframe(df[view_cols].round(2), use_container_width=True)
