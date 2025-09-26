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

# ── 401(k) inputs ────────────────────────────────────────────────────────────
st.sidebar.subheader("401(k) Inputs")

# Starting balance (at day 0; Year 1 begins immediately—no Year 0 row)
current_savings = st.sidebar.number_input(
    "Current Savings (Starting balance at day 0)",
    min_value=0.0, max_value=10_000_000.0, value=0.0, step=1_000.0
)

# 🔹 Contribution Mode Toggle — COMMENTED OUT (fixed-dollar only)
# contrib_mode = st.sidebar.radio("Contribution Mode", ["Fixed Dollar Amount", "Percent of Salary"], index=0)
contrib_mode = "Fixed Dollar Amount"

# ▶▶ EXACT TWO-INPUT BOXES (as requested)
with st.sidebar.expander("Initial Contribution Schedule", expanded=True):
    init_age = st.number_input("Initial Start Age", 18, 80, 35, 1)
    init_contrib = st.number_input("Initial contribution amount", 1000, 1_000_000, 50_000, 1_000)

with st.sidebar.expander("Second Contribution Schedule", expanded=True):
    second_age_default = max(50, int(init_age))
    second_age = st.number_input("Second Start Age", int(init_age), 80, second_age_default, 1)
    second_contrib = st.number_input("Second contribution amount", 1000, 1_000_000, 55_000, 1_000)

# Keep the toggle outside the boxes to keep each box to exactly two fields
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
# Year 1 starts at day 0 and runs to day 365. NO Year 0 row is created.
years = int(ret_age - init_age)              # Year = 1..years
total_periods = years * periods_per_year

balance = float(current_savings)             # starting balance at day 0
cum_contrib = 0.0
cum_earnings = 0.0

annual_data = []                             # captured at END of each plan year
annual_contrib_for_year = 0.0

employee_contrib_per_period = 0.0
employer_rate_effective = float(employer_contrib_rate)

for period in range(total_periods):
    # period runs 0..total_periods-1
    year_idx = period // periods_per_year            # 0-based year index (Year 1 -> index 0)
    pos_in_year = period % periods_per_year
    is_year_start = (pos_in_year == 0)
    is_year_end = (pos_in_year == periods_per_year - 1)

    # Age at the start of this plan year (displayed on the Year row)
    age_start = int(init_age) + year_idx

    # Set this year's contribution schedule at the START of the year
    if is_year_start:
        if use_second and age_start >= int(second_age):
            contrib_annual = float(second_contrib)
        else:
            contrib_annual = float(init_contrib)

        employee_contrib_per_period = contrib_annual / periods_per_year
        annual_contrib_for_year = 0.0  # reset yearly accumulator

    # Employer per-period based on effective rate
    employer_amt = employee_contrib_per_period * employer_rate_effective
    total_contrib = employee_contrib_per_period + employer_amt

    # Deposit at the START of the period (day 0), then earn for the period
    balance += total_contrib
    earnings = balance * rate_per_period
    balance += earnings

    # Accumulate trackers
    annual_contrib_for_year += total_contrib
    cum_contrib += total_contrib
    cum_earnings += earnings

    # Capture row at END of the year
    if is_year_end:
        year_number = year_idx + 1
        age_end = age_start + 1
        annual_data.append({
            "Year": year_number,
            "Age": int(age_start),
            "AgeEnd": int(age_end),
            "StartingSavings": float(current_savings),   # flat band to keep top == Total
            "YearlyContrib": annual_contrib_for_year,
            "Contributions": cum_contrib,
            "Earnings": cum_earnings,
            "Total": balance
        })

# Build DataFrame
df = pd.DataFrame(annual_data)

# ── KPI Metrics ───────────────────────────────────────────────────────────────
end_balance = float(df["Total"].iloc[-1]) if not df.empty else 0.0
end_contrib = float(df["Contributions"].iloc[-1]) if not df.empty else 0.0
end_earnings = float(df["Earnings"].iloc[-1]) if not df.empty else 0.0

col1, col2, col3 = st.columns(3)
col1.metric("💰 Ending Balance", f"${end_balance:,.0f}")
col2.metric("📥 Contributions (incl. employer)", f"${end_contrib:,.0f}")
col3.metric("📈 Earnings", f"${end_earnings:,.0f}")

# ── Chart ─────────────────────────────────────────────────────────────────────
# Wider aspect to fill horizontally; legend moved below; margins tuned so nothing overlaps
fig, ax = plt.subplots(figsize=(14, 5))  # wide figure to fill page
fig.patch.set_facecolor("#f7f7f7" if "Light" in theme else "#111418")
ax.set_facecolor("#ffffff" if "Light" in theme else "#0c0f13")

years_x = df["Year"]
bottoms = np.zeros(len(df))
bar_width = 0.90

# Flat baseline band (StartingSavings) to keep stacks matching Total
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

# Legend BELOW the plot so it never covers bars
legend = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=True)

ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
ax.grid(axis='y', linestyle='--', alpha=0.6)

# Tight x-margins to fill horizontally
if not df.empty:
    ax.set_xlim(df["Year"].min() - 0.5, df["Year"].max() + 0.5)
ax.margins(x=0.01)

# Headroom—kept modest so labels sit LOWER (near bar tops), not floating
max_total = float(df["Total"].max()) if not df.empty else 1.0
_, ymax = ax.get_ylim()
target_top = max_total * 1.22  # ~22% headroom keeps labels low but off bars
if ymax < target_top:
    ax.set_ylim(top=target_top)

# Leave space for bottom legend and keep everything visible
plt.subplots_adjust(left=0.10, right=0.98, top=0.92, bottom=0.28)
plt.tight_layout()

# ── Milestone callouts (lower, age-based) ─────────────────────────────────────
def y_total_at_year(year_num: int):
    row = df.loc[df["Year"] == int(year_num)]
    if row.empty:
        return None
    return float(row["Total"].iloc[0])

def add_callouts_low(points, y_gap_frac=0.05):
    """
    Place annotations just above the bar tops with small vertical spacing so
    they remain LOW (near bars) and do not overlap each other or the bars.
    """
    if not points:
        return
    _ymin, _ymax = ax.get_ylim()
    gap = y_gap_frac * _ymax
    # Sort by x (timeline)
    pts = sorted(points, key=lambda p: p["x"])
    last_y_text = -np.inf
    for p in pts:
        base = p["y"] + gap
        y_text = max(base, last_y_text + gap)  # stagger if needed
        y_text = min(y_text, _ymax * 0.97)
        ax.annotate(
            p["label"],
            xy=(p["x"], p["y"]),
            xytext=(p["x"], y_text),
            textcoords="data",
            arrowprops=dict(facecolor="black", arrowstyle="->", lw=1),
            fontsize=9,
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.25",
                      fc="#ffffff" if "Light" in theme else "#1b1f24",
                      ec="#cfcfcf" if "Light" in theme else "#333333"),
            zorder=10
        )
        last_y_text = y_text

callouts = []

# 1) Initial (Year 1) — label uses amount + AGE (not year number)
y1 = y_total_at_year(1)
if y1 is not None:
    callouts.append({
        "x": 1,
        "y": y1,
        "label": f"Initial contribution: ${init_contrib:,.0f}\nAge: {int(init_age)}"
    })

# 2) Second schedule start — label uses amount + Second Start AGE
if use_second and int(second_age) >= int(init_age):
    second_year_num = int(second_age) - int(init_age) + 1
    ys = y_total_at_year(second_year_num)
    if ys is not None:
        callouts.append({
            "x": second_year_num,
            "y": ys,
            "label": f"Second contribution: ${second_contrib:,.0f}\nAge: {int(second_age)}"
        })

# 3) Retirement — keep for context; age-based
last_year_num = int(years)
yr = y_total_at_year(last_year_num)
if yr is not None:
    callouts.append({
        "x": last_year_num,
        "y": yr,
        "label": f"Retirement\nAge: {int(ret_age)}\nTotal: ${yr:,.0f}"
    })

if show_callouts:
    add_callouts_low(callouts)

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

# Render chart (fills the page horizontally)
st.pyplot(fig, use_container_width=True)

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
# Show Age as start-of-year age for Year >= 1.
view_cols = [
    "Year",
    "Age",
    "StartingSavings",
    "YearlyContrib", "Contributions", "Earnings", "Total"
]
st.dataframe(df[view_cols].round(2), use_container_width=True)