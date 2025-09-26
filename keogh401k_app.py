import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import io

# ✅ Page config
st.set_page_config(page_title="Keogh/401(k) Projection", layout="wide")

# ── Title and icon ────────────────────────────────────────────────────────────
img_col, title_col = st.columns([0.15, 0.85])
with img_col:
    st.image("Image_2.png", use_container_width=True)
with title_col:
    st.title("Future Value Calculator for Keogh/401(k)")

# ── Sidebar: Theme + Inputs ───────────────────────────────────────────────────
st.sidebar.title("Display & Inputs")

theme = st.sidebar.radio(
    "Theme",
    options=["Light (projector-friendly default)", "Dark (high-contrast)"],
    index=0,
    key="theme_mode",
)

color_schemes = {
    "Blues": ("#377eb8", "#4daf4a"),
    "Grays": ("#999999", "#666666"),
    "Red & Blue": ("#e41a1c", "#377eb8"),
    "Purples": ("#984ea3", "#7570b3"),
    "Orange & Teal": ("#ff7f00", "#1b9e77"),
    "Blue & Orange (good for projectors)": ("#377eb8", "#ff7f00"),
    "Teal & Purple (good for projectors)": ("#1b9e77", "#984ea3"),
    "Blue & Gray (good for projectors)": ("#377eb8", "#666666"),
}
selected_scheme = st.sidebar.selectbox("Select Color Scheme", list(color_schemes.keys()))
contrib_color, earnings_color = color_schemes[selected_scheme]
starting_color = "#d1d5db" if "Light" in theme else "#4b5563"

# 🔘 Toggle to show/hide milestone labels (callouts)
show_callouts = st.sidebar.checkbox("Show milestone callouts (labels)", value=True)

# ➕ Layout controls (lets you 'move' labels/legend without code edits)
st.sidebar.markdown("### Chart Layout Controls")
legend_position = st.sidebar.selectbox(
    "Legend position",
    ["Below (center)", "Upper right", "Upper left", "Best (auto)"],
    index=0
)
callout_height_factor = st.sidebar.slider(
    "Callout line height (0.30 = low • 0.80 = high)",
    min_value=0.30, max_value=0.80, value=0.50, step=0.02
)
callout_line_halfwidth = st.sidebar.slider(
    "Callout horizontal line half-width (bars)",
    min_value=0.10, max_value=0.60, value=0.35, step=0.05
)
callout_text_gap = st.sidebar.slider(
    "Gap between line and label (as % of axis height)",
    min_value=0.01, max_value=0.08, value=0.03, step=0.01
)

# ── 401(k) inputs ────────────────────────────────────────────────────────────
st.sidebar.subheader("401(k) Inputs")

# Starting balance at day 0 (Year 1 includes it; NO Year 0 row)
current_savings = st.sidebar.number_input(
    "Current Savings (Starting balance at day 0)",
    min_value=0.0, max_value=10_000_000.0, value=0.0, step=1_000.0
)

# 🔹 Contribution Mode Toggle — COMMENTED OUT (fixed-dollar only)
# contrib_mode = st.sidebar.radio("Contribution Mode", ["Fixed Dollar Amount", "Percent of Salary"], index=0)
contrib_mode = "Fixed Dollar Amount"

# ▶▶ EXACT TWO-INPUT BOXES (per your spec)
with st.sidebar.expander("Initial Contribution Schedule", expanded=True):
    init_age = st.number_input("Initial Start Age", 18, 80, 35, 1)
    init_contrib = st.number_input("Initial contribution amount", 1000, 1_000_000, 50_000, 1_000)

with st.sidebar.expander("Second Contribution Schedule", expanded=True):
    second_age_default = max(50, int(init_age))
    second_age = st.number_input("Second Start Age", int(init_age), 80, second_age_default, 1)
    second_contrib = st.number_input("Second contribution amount", 1000, 1_000_000, 55_000, 1_000)

# Keep the toggle outside the boxes so each box contains exactly the two fields you wanted
use_second = st.sidebar.checkbox("Use second contribution schedule", value=True)

# Percent-of-salary inputs — ENTIRELY COMMENTED OUT (kept, not active)
# if contrib_mode == "Percent of Salary":
#     base_salary = st.sidebar.number_input("Current Salary", 10_000.0, 1_000_000.0, 120_000.0, 1_000.0)
#     init_percent = st.sidebar.slider("Employee Contribution % (initial)", 0.0, 100.0, 10.0, 0.5)
#     second_percent = st.sidebar.slider("Employee Contribution % (second schedule)", 0.0, 100.0, 12.0, 0.5)
#     annual_raise = st.sidebar.slider("Annual Pay Increase %", 0.0, 10.0, 3.0, 0.1)
# else:
#     base_salary = 0.0
#     init_percent = None
#     second_percent = None
#     annual_raise = 0.0

# Employer contribution rate and returns
employer_contrib_rate = st.sidebar.number_input("Employer contribution % (0.00–1.00)", 0.0, 1.0, 0.0, 0.01)
annual_return = st.sidebar.number_input("Annual Return Rate (0.00–0.20)", 0.0, 0.20, 0.06, 0.01)

ret_age = st.sidebar.number_input(
    "Retirement Age", min_value=int(init_age) + 1, max_value=100, value=max(65, int(init_age) + 1), step=1
)

frequency = st.sidebar.selectbox("Compounding Frequency", ["biweekly", "monthly", "quarterly"])
periods_per_year = {"biweekly": 26, "monthly": 12, "quarterly": 4}[frequency]
rate_per_period = (1 + annual_return) ** (1 / periods_per_year) - 1

# Guardrail
if use_second and second_age < init_age:
    st.error("Second Start Age cannot be before Initial Start Age.")
    st.stop()

# ── Projection calculation ────────────────────────────────────────────────────
# Year 1 spans day 0–365. NO Year 0 row.
years = int(ret_age - init_age)              # Year = 1..years
total_periods = years * periods_per_year

balance = float(current_savings)             # starting balance at day 0
cum_contrib = 0.0
cum_earnings = 0.0

annual_data = []                             # capture END of each plan year
annual_contrib_for_year = 0.0

employee_contrib_per_period = 0.0
employer_rate_effective = float(employer_contrib_rate)

for period in range(total_periods):
    year_idx = period // periods_per_year
    pos_in_year = period % periods_per_year
    is_year_start = (pos_in_year == 0)
    is_year_end = (pos_in_year == periods_per_year - 1)
    age_start = int(init_age) + year_idx

    if is_year_start:
        if use_second and age_start >= int(second_age):
            contrib_annual = float(second_contrib)
        else:
            contrib_annual = float(init_contrib)
        employee_contrib_per_period = contrib_annual / periods_per_year
        annual_contrib_for_year = 0.0

    employer_amt = employee_contrib_per_period * employer_rate_effective
    total_contrib = employee_contrib_per_period + employer_amt

    # Deposit at start of period, then earn for the period
    balance += total_contrib
    earnings = balance * rate_per_period
    balance += earnings

    annual_contrib_for_year += total_contrib
    cum_contrib += total_contrib
    cum_earnings += earnings

    if is_year_end:
        year_number = year_idx + 1
        age_end = age_start + 1
        annual_data.append({
            "Year": year_number,
            "Age": int(age_start),
            "AgeEnd": int(age_end),
            "StartingSavings": float(current_savings),   # flat band so stack top == Total
            "YearlyContrib": annual_contrib_for_year,
            "Contributions": cum_contrib,
            "Earnings": cum_earnings,
            "Total": balance
        })

df = pd.DataFrame(annual_data)

# ── KPI Metrics ───────────────────────────────────────────────────────────────
end_balance = float(df["Total"].iloc[-1]) if not df.empty else 0.0
end_contrib = float(df["Contributions"].iloc[-1]) if not df.empty else 0.0
end_earnings = float(df["Earnings"].iloc[-1]) if not df.empty else 0.0

col1, col2, col3 = st.columns(3)
col1.metric("💰 Ending Balance", f"${end_balance:,.0f}")
col2.metric("📥 Contributions (incl. employer)", f"${end_contrib:,.0f}")
col3.metric("📈 Earnings", f"${end_earnings:,.0f}")

# ── Chart (normal aspect, not stretched) ──────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))  # normal size like before
fig.patch.set_facecolor("#f7f7f7" if "Light" in theme else "#111418")
ax.set_facecolor("#ffffff" if "Light" in theme else "#0c0f13")

years_x = df["Year"]
bar_width = 0.85

# Draw baseline + stacks
bottoms = np.zeros(len(df))
if current_savings >= 0:
    ax.bar(years_x, df["StartingSavings"], color=starting_color, edgecolor="none",
           label="Starting Savings", zorder=1, width=bar_width)
    bottoms = df["StartingSavings"].values

ax.bar(years_x, df["Contributions"], bottom=bottoms, color=contrib_color, edgecolor="none",
       label="Contributions", zorder=2, width=bar_width)
ax.bar(years_x, df["Earnings"], bottom=bottoms + df["Contributions"], color=earnings_color, edgecolor="none",
       label="Earnings", zorder=3, width=bar_width)

ax.set_xlabel("Year (1 = first plan year)")
ax.set_ylabel("Amount ($)")
ax.set_title("Future Value Calculation", fontsize=11)
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
ax.grid(axis='y', linestyle='--', alpha=0.6)

# Tight x-limits and margins
if not df.empty:
    ax.set_xlim(df["Year"].min() - 0.5, df["Year"].max() + 0.5)
ax.margins(x=0.02)

# Headroom so callout line can sit above bars (we’ll refine after computing lines)
max_total = float(df["Total"].max()) if not df.empty else 1.0
_, y_top_initial = ax.get_ylim()
# Start with modest headroom; we’ll expand if needed for line height
target_top = max_total * 1.20
if y_top_initial < target_top:
    ax.set_ylim(top=target_top)

# ── Legend below (or alternative positions via control) ───────────────────────
def apply_legend():
    if legend_position == "Below (center)":
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=True)
        plt.subplots_adjust(bottom=0.25, top=0.90)  # space for legend
    elif legend_position == "Upper right":
        ax.legend(loc="upper right", frameon=True)
        plt.subplots_adjust(bottom=0.12, top=0.92)
    elif legend_position == "Upper left":
        ax.legend(loc="upper left", frameon=True)
        plt.subplots_adjust(bottom=0.12, top=0.92)
    else:  # Best (auto)
        ax.legend(loc="best", frameon=True)
        plt.subplots_adjust(bottom=0.12, top=0.92)

apply_legend()

# ── Helper: y at bar top for a given Year ─────────────────────────────────────
def y_total_at_year(year_num: int):
    row = df.loc[df["Year"] == int(year_num)]
    if row.empty:
        return None
    return float(row["Total"].iloc[0])

# ── Callouts: horizontal line above label, arrow down to bar top ─────────────
def add_callouts_with_line(points):
    """
    Draws a horizontal leader line above each bar top and places the label
    BELOW that line (so labels stay lower). No arrow or cross marker.
    Expands y-limits if needed so lines/labels always fit.
    """
    if not points:
        return

    hf = float(globals().get("callout_height_factor", 0.50))       # 0..1 between bar top and axis top
    halfw = float(globals().get("callout_line_halfwidth", 0.35))   # horizontal line half-width
    gap_frac = float(globals().get("callout_text_gap", 0.03))      # gap between line and label
    min_above_frac = 0.02                                          # minimum gap above bar top

    light_mode = ("Light" in theme) if isinstance(theme, str) else True
    box_fc = "#ffffff" if light_mode else "#1b1f24"
    box_ec = "#cfcfcf" if light_mode else "#333333"
    line_color = "#333333"

    ymin, ymax = ax.get_ylim()
    desired_tops = []
    for p in points:
        y_bar = float(p["y"])
        y_line = y_bar + (ymax - y_bar) * hf
        desired_tops.append(y_line * 1.06)
    if desired_tops:
        needed_top = max(ymax, max(desired_tops))
        if needed_top > ymax:
            ax.set_ylim(top=needed_top)

    ymin, ymax = ax.get_ylim()
    text_gap_abs = gap_frac * ymax
    min_above_abs = min_above_frac * ymax

    for p in points:
        x = float(p["x"])
        y_bar = float(p["y"])
        y_line = y_bar + (ymax - y_bar) * hf

        # Horizontal leader line
        ax.plot([x - halfw, x + halfw], [y_line, y_line],
                color=line_color, lw=1.2, zorder=9)

        # Label BELOW the line but ABOVE the bar
        y_text = max(y_bar + min_above_abs, y_line - text_gap_abs)
        ax.text(
            x, y_text, p["label"],
            ha="center", va="top", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.25", fc=box_fc, ec=box_ec),
            zorder=10
        )


# Build callouts using AGE + AMOUNT (no 'Year 16')
callouts = []

# 1) Initial (Year 1)
y1 = y_total_at_year(1)
if y1 is not None:
    callouts.append({
        "x": 1,
        "y": y1,
        "label": f"Initial contribution: ${init_contrib:,.0f}\nAge: {int(init_age)}"
    })

# 2) Second schedule (by AGE)
if use_second and int(second_age) >= int(init_age):
    second_year_num = int(second_age) - int(init_age) + 1
    ys = y_total_at_year(second_year_num)
    if ys is not None:
        callouts.append({
            "x": second_year_num,
            "y": ys,
            "label": f"Second contribution: ${second_contrib:,.0f}\nAge: {int(second_age)}"
        })

# 3) Retirement
last_year_num = int(years)
yr = y_total_at_year(last_year_num)
if yr is not None:
    callouts.append({
        "x": last_year_num,
        "y": yr,
        "label": f"Retirement\nAge: {int(ret_age)}\nTotal: ${yr:,.0f}"
    })

# Add callouts (lower labels, line above, arrow down)
if show_callouts:
    add_callouts_with_line(callouts)

# Render chart (normal—not stretched)
st.pyplot(fig)  # no use_container_width -> looks like a classic chart

# ✅ Export Chart (PNG)
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

# ── Export Table ──────────────────────────────────────────────────────────────
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
view_cols = [
    "Year", "Age", "StartingSavings",
    "YearlyContrib", "Contributions", "Earnings", "Total"
]
st.dataframe(df[view_cols].round(2), use_container_width=True)