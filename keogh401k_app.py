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

# Optional current savings (added at day 0 BEFORE first paycheck; Year 1 will include its growth but no 'Year 0' row)
current_savings = st.sidebar.number_input(
    "Current Savings (Starting balance at day 0)",
    min_value=0.0, max_value=10_000_000.0, value=0.0, step=1_000.0
)

# 🔹 Contribution Mode Toggle — COMMENTED OUT (fixed-dollar only)
# contrib_mode = st.sidebar.radio("Contribution Mode", ["Fixed Dollar Amount", "Percent of Salary"], index=0)
contrib_mode = "Fixed Dollar Amount"

# ▶▶ EXACT TWO-INPUT BOXES as requested
box1 = st.sidebar.container(border=True)
with box1:
    st.markdown("**Initial Contribution Schedule**")
    init_age = st.number_input("Initial Start Age", 18, 80, 35, 1)
    init_contrib = st.number_input("Initial contribution amount", 1000, 1_000_000, 50_000, 1_000)

box2 = st.sidebar.container(border=True)
with box2:
    st.markdown("**Second Contribution Schedule**")
    second_age_default = max(50, int(init_age))
    second_age = st.number_input("Second Start Age", int(init_age), 80, second_age_default, 1)
    second_contrib = st.number_input("Second contribution amount", 1000, 1_000_000, 55_000, 1_000)

# Keep the toggle outside the boxes to avoid mixing fields inside each box
use_second = st.sidebar.checkbox("Use second contribution schedule", value=True)

# Percent-of-salary inputs — ENTIRELY COMMENTED OUT
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
# ◀◀ IMPORTANT: Year 1 starts at day 0-365. There is NO Year 0 row.
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
    # period runs 0..total_periods-1
    year_idx = period // periods_per_year            # 0-based year index (Year 1 corresponds to index 0)
    pos_in_year = period % periods_per_year
    is_year_start = (pos_in_year == 0)
    is_year_end = (pos_in_year == periods_per_year - 1)

    # Age at the start of this plan year (this will display for that Year row)
    age_start = int(init_age) + year_idx

    # Set this year's contribution schedule at the START of the year
    if is_year_start:
        if use_second and age_start >= int(second_age):
            contrib_annual = float(second_contrib)
        else:
            contrib_annual = float(init_contrib)

        employee_contrib_per_period = contrib_annual / periods_per_year
        annual_contrib_for_year = 0.0  # reset yearly accumulator

    # Employer per-period based on effective rate (no IRS caps in this simplified version)
    employer_amt = employee_contrib_per_period * employer_rate_effective
    total_contrib = employee_contrib_per_period + employer_amt

    # Deposit at the START of the period (day 0), then earn for the period
    balance += total_contrib
    earnings = balance * rate_per_period
    balance += earnings

    # Accumulate year + cumulative trackers
    annual_contrib_for_year += total_contrib
    cum_contrib += total_contrib
    cum_earnings += earnings

    # Capture row at END of the year (so Year 1 has full-year totals)
    if is_year_end:
        year_number = year_idx + 1                 # 1-based Year numbering (1..years)
        age_end = age_start + 1                    # end-of-year integer age
        annual_data.append({
            "Year": year_number,
            "Age": int(age_start),                 # start-of-year age (e.g., 35 for Year 1)
            "AgeEnd": int(age_end),
            "StartingSavings": float(current_savings),   # flat baseline band to ensure top == Total
            "YearlyContrib": annual_contrib_for_year,    # this year's contributions (incl. employer)
            "Contributions": cum_contrib,                # cumulative contributions
            "Earnings": cum_earnings,                    # cumulative earnings
            "Total": balance                              # end-of-year balance
        })

# Build DataFrame (no Year 0 row)
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
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor("#f7f7f7" if "Light" in theme else "#111418")
ax.set_facecolor("#ffffff" if "Light" in theme else "#0c0f13")

# Stacked bars with a flat "StartingSavings" baseline band so top == Total
years_x = df["Year"]
bottoms = np.zeros(len(df))
if current_savings >= 0:
    ax.bar(years_x, df["StartingSavings"], color=starting_color, edgecolor="none",
           label="Starting Savings", zorder=1)
    bottoms = df["StartingSavings"].values

ax.bar(years_x, df["Contributions"], bottom=bottoms, color=contrib_color, edgecolor="none",
       label="Contributions", zorder=2)
ax.bar(years_x, df["Earnings"], bottom=bottoms + df["Contributions"], color=earnings_color, edgecolor="none",
       label="Earnings", zorder=3)

ax.set_xlabel("Year (1 = first plan year, spans day 0–365)")
ax.set_ylabel("Amount ($)")
ax.set_title("Future Value Calculation", fontsize=11)
# Move legend outside to guarantee it never covers bars
ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True)
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
ax.grid(axis='y', linestyle='--', alpha=0.6)

# Extra headroom so annotations NEVER touch bars
max_total = float(df["Total"].max()) if not df.empty else 1.0
min_y, ymax = ax.get_ylim()
target_top = max_total * 1.45  # generous headroom
if ymax < target_top:
    ax.set_ylim(top=target_top)

plt.subplots_adjust(right=0.82)  # room for outside legend
plt.tight_layout()

# ── Milestone callouts placed ABOVE bars (no overlap) ─────────────────────────
def add_callouts_above(points, y_gap_frac=0.08):
    """
    Place all annotations above the bar tops with vertical spacing to avoid overlap.
    No label ever sits on a bar.
    points: list of dicts with keys {x, y, label}
    """
    if not points:
        return
    _ymin, _ymax = ax.get_ylim()
    gap = y_gap_frac * _ymax
    # Sort by x (timeline) but enforce increasing y_text
    pts = sorted(points, key=lambda p: p["x"])
    last_y_text = max_total * 1.02  # start a bit above the max bar top
    for p in pts:
        y_text = max(p["y"] + gap, last_y_text + gap)
        y_text = min(y_text, _ymax * 0.98)  # stay within the top margin
        ax.annotate(
            p["label"],
            xy=(p["x"], p["y"]),
            xytext=(p["x"], y_text),
            textcoords="data",
            arrowprops=dict(facecolor="black", arrowstyle="->", lw=1),
            fontsize=9,
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.3",
                      fc="#ffffff" if "Light" in theme else "#1b1f24",
                      ec="#cfcfcf" if "Light" in theme else "#333333"),
            zorder=10
        )
        last_y_text = y_text

def y_total_at_year(year_num: int):
    row = df.loc[df["Year"] == int(year_num)]
    if row.empty:
        return None
    return float(row["Total"].iloc[0])

callouts = []

# 1) Initial Start Year (Year 1)
y1 = y_total_at_year(1)
if y1 is not None:
    callouts.append({
        "x": 1,
        "y": y1,
        "label": f"Initial Start Year\nYear 1 | Age: {int(init_age)}\nTotal: ${y1:,.0f}"
    })

# 2) Second contribution start (at beginning of 'second_age' year)
if use_second and int(second_age) >= int(init_age):
    second_year_num = int(second_age) - int(init_age) + 1  # with Year 1 at init_age
    ys = y_total_at_year(second_year_num)
    if ys is not None:
        callouts.append({
            "x": second_year_num,
            "y": ys,
            "label": f"Second Contribution Starts\nYear {second_year_num} | Age: {int(second_age)}\nTotal: ${ys:,.0f}"
        })

# 3) Retirement (last year)
last_year_num = int(years)
yr = y_total_at_year(last_year_num)
if yr is not None:
    callouts.append({
        "x": last_year_num,
        "y": yr,
        "label": f"Retirement\nYear {last_year_num} | Age: {int(ret_age)}\nTotal: ${yr:,.0f}"
    })

# Honor the "Show milestone callouts" toggle
if show_callouts:
    add_callouts_above(callouts)

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

# Render chart
st.pyplot(fig)

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
] + (["StartingSavings"] if current_savings >= 0 else []) + [
    "YearlyContrib", "Contributions", "Earnings", "Total"
]
st.dataframe(df[view_cols].round(2), use_container_width=True)
