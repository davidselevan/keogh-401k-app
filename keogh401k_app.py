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

# ➕ Layout controls
st.sidebar.markdown("### Chart Layout Controls")
legend_position = st.sidebar.selectbox(
    "Legend position", ["Below (center)", "Upper right", "Upper left", "Best (auto)"], index=0
)
callout_height_factor = st.sidebar.slider(
    "Callout line height (0.30 = low • 0.80 = high)", 0.30, 0.80, 0.50, 0.02
)
callout_text_gap = st.sidebar.slider(
    "Gap between line and label (as % of axis height)", 0.01, 0.08, 0.03, 0.01
)

# ── 401(k) inputs ────────────────────────────────────────────────────────────
st.sidebar.subheader("401(k) Inputs")

# Day 0 starting balance (we WILL create Year 0 row)
current_savings = st.sidebar.number_input(
    "Current Savings (Starting balance at day 0)",
    min_value=0.0, max_value=10_000_000.0, value=0.0, step=1_000.0
)

with st.sidebar.expander("Initial Contribution Schedule", expanded=True):
    init_age = st.number_input("Initial Start Age", 18, 80, 35, 1)
    init_contrib = st.number_input("Initial contribution amount", 1000, 1_000_000, 50_000, 1_000)

with st.sidebar.expander("Second Contribution Schedule", expanded=True):
    second_age_default = max(50, int(init_age))
    second_age = st.number_input("Second Start Age", int(init_age), 80, second_age_default, 1)
    second_contrib = st.number_input("Second contribution amount", 1000, 1_000_000, 55_000, 1_000)

use_second = st.sidebar.checkbox("Use second contribution schedule", value=True)

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
# Start at day 0 with a Year 0 baseline; compound from day 1 of Year 1.
# Run through END of retirement year (inclusive): simulate (ret_age - init_age) full years.
years = int(ret_age - init_age) + 1        # e.g., 65-35=30 years
total_periods = years * periods_per_year

balance = float(current_savings)        # day 0 baseline
cum_contrib = 0.0
cum_earnings = 0.0

annual_data = []                        # Year 0 + end-of-year rows
annual_contrib_for_year = 0.0

# ✅ Year 0 baseline row (day 0). Age intentionally blank to avoid duplicate "35".
annual_data.append({
    "Year": 0,
    "AgeStart": int(init_age),
    "AgeEnd": int(init_age),
    "Age": "",                   # display column (blank for Year 0)
    "StartingSavings": balance,
    "YearlyContrib": 0.0,        # Year 0 has no contributions
    "Contributions": 0.0,        # cumulative
    "Earnings": 0.0,             # cumulative
    "Total": balance
})

employee_contrib_per_period = 0.0
for period in range(total_periods):
    year_idx = period // periods_per_year            # 0..years-1
    pos_in_year = period % periods_per_year
    is_year_start = (pos_in_year == 0)
    is_year_end   = (pos_in_year == periods_per_year - 1)

    age_start = int(init_age) + year_idx            # label by START-OF-YEAR age

    # Set this year's contribution schedule at the START of the year (day 1)
    if is_year_start:
        contrib_annual = float(second_contrib) if (use_second and age_start >= int(second_age)) else float(init_contrib)
        employee_contrib_per_period = contrib_annual / periods_per_year
        annual_contrib_for_year = 0.0

    # Deposit at start of period, then earn for the period
    employer_amt  = employee_contrib_per_period * float(employer_contrib_rate)
    total_contrib = employee_contrib_per_period + employer_amt
    balance += total_contrib
    earnings = balance * rate_per_period
    balance += earnings

    # Accumulate trackers
    annual_contrib_for_year += total_contrib
    cum_contrib += total_contrib
    cum_earnings += earnings

    # Capture row at END of each plan year (Year 1..years)
    if is_year_end:
        year_number = year_idx + 1                    # 1..years
        age_end = age_start + 1
        annual_data.append({
            "Year": year_number,
            "AgeStart": int(age_start),               # e.g., 35 for Year 1
            "AgeEnd": int(age_end),                   # e.g., 36 for Year 1
            "Age": int(age_start),                    # 🔑 display start-of-year age (Year 1 shows 35)
            "StartingSavings": float(current_savings),
            "YearlyContrib": annual_contrib_for_year, # this year's employee+employer sum
            "Contributions": cum_contrib,             # cumulative
            "Earnings": cum_earnings,                 # cumulative
            "Total": balance                          # end-of-year balance
        })

# Build DataFrame (for chart/callouts keep Year 0; for table/export hide it)
df = pd.DataFrame(annual_data)
df_table = df.loc[df["Year"] != 0].copy()  # 🔒 hide Year 0 from the table & file export

# ── KPI Metrics ───────────────────────────────────────────────────────────────
end_balance = float(df["Total"].iloc[-1]) if not df.empty else 0.0
end_contrib = float(df["Contributions"].iloc[-1]) if not df.empty else 0.0
end_earnings = float(df["Earnings"].iloc[-1]) if not df.empty else 0.0

col1, col2, col3 = st.columns(3)
col1.metric("💰 Ending Balance", f"${end_balance:,.0f}")
col2.metric("📥 Contributions (incl. employer)", f"${end_contrib:,.0f}")
col3.metric("📈 Earnings", f"${end_earnings:,.0f}")

# ── Chart (index-based x positions so every bar shows) ────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor("#f7f7f7" if "Light" in theme else "#111418")
ax.set_facecolor("#ffffff" if "Light" in theme else "#0c0f13")

positions = np.arange(len(df))   # 0..N including Year 0
bar_width = 0.85

# Stacked bars: StartingSavings (flat band) + cumulative Contributions + cumulative Earnings
ax.bar(positions, df["StartingSavings"], color=starting_color, edgecolor="none",
       label="Starting Savings", zorder=1, width=bar_width)
ax.bar(positions, df["Contributions"], bottom=df["StartingSavings"], color=contrib_color,
       edgecolor="none", label="Contributions", zorder=2, width=bar_width)
ax.bar(positions, df["Earnings"], bottom=df["StartingSavings"] + df["Contributions"], color=earnings_color,
       edgecolor="none", label="Earnings", zorder=3, width=bar_width)

# 🔁 X-axis: numeric Year labels starting at 0
ax.set_xticks(positions)
ax.set_xticklabels(df["Year"].astype(int).astype(str), rotation=0)
ax.set_xlabel("Year (0 = Day 0 baseline; then 1..N)")
ax.set_ylabel("Amount ($)")
ax.set_title("Future Value Calculation", fontsize=11)
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
ax.grid(axis='y', linestyle='--', alpha=0.6)

# Tight x-limits and margins
ax.set_xlim(-0.5, positions[-1] + 0.5)
ax.margins(x=0.02)

# Headroom for callouts
max_total = float(df["Total"].max()) if not df.empty else 1.0
_, y_top_initial = ax.get_ylim()
target_top = max_total * 1.20
if y_top_initial < target_top:
    ax.set_ylim(top=target_top)

# Legend placement
def apply_legend():
    if legend_position == "Below (center)":
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=True)
        plt.subplots_adjust(bottom=0.25, top=0.90)
    elif legend_position == "Upper right":
        ax.legend(loc="upper right", frameon=True); plt.subplots_adjust(bottom=0.12, top=0.92)
    elif legend_position == "Upper left":
        ax.legend(loc="upper left", frameon=True); plt.subplots_adjust(bottom=0.12, top=0.92)
    else:
        ax.legend(loc="best", frameon=True); plt.subplots_adjust(bottom=0.12, top=0.92)

apply_legend()

# ── Helpers for callouts (use index positions so they align with bars) ────────
def total_and_index_for_yearnum(year_num: int):
    row = df.loc[df["Year"] == int(year_num)]
    if row.empty:
        return None, None
    idx = int(row.index[0])
    return float(row["Total"].iloc[0]), idx

def add_callouts_vertical(points):
    """Place label box ABOVE the leader line (not on it)."""
    if not points:
        return

    height_factor = float(globals().get("callout_height_factor", 0.55))  # 0..1 of headroom used
    text_gap_frac = float(globals().get("callout_text_gap", 0.03))       # gap above line top
    min_above_frac = 0.02

    # Theme-aware box color
    light_mode = ("Light" in theme) if isinstance(theme, str) else True
    box_fc = "#ffffff" if light_mode else "#1b1f24"
    box_ec = "#cfcfcf" if light_mode else "#333333"
    line_color = "#333333"

    ymin, ymax = ax.get_ylim()
    min_above_abs = min_above_frac * ymax
    text_gap_abs = text_gap_frac * ymax

    # Pre-expand y-limit if needed for tallest label
    desired_tops = []
    for p in points:
        y_bar = float(p["y"])
        y_line_top = y_bar + max(0.18 * ymax, (ymax - y_bar) * height_factor)
        desired_tops.append(y_line_top + text_gap_abs + 0.02 * ymax)
    if desired_tops:
        need_top = max([ymax] + desired_tops)
        if need_top > ymax:
            ax.set_ylim(top=need_top)
            _, ymax = ax.get_ylim()
            min_above_abs = min_above_frac * ymax
            text_gap_abs = text_gap_frac * ymax

    for p in points:
        x, y_bar = float(p["x"]), float(p["y"])
        y_line_top = y_bar + max(0.18 * ymax, (ymax - y_bar) * height_factor)

        # Draw vertical leader; label box ABOVE the line top
        ax.annotate("", xy=(x, y_bar), xytext=(x, y_line_top),
                    arrowprops=dict(arrowstyle="->", lw=1.2, color=line_color), zorder=5)

        y_text = max(y_bar + min_above_abs, y_line_top + text_gap_abs)
        ax.text(x, y_text, p["label"], ha="center", va="bottom", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.25", fc=box_fc, ec=box_ec), zorder=6)

# ── Callouts (per spec) ──────────────────────────────────────────────────────
callouts = []

# 1) Initial Year (Year 1): keep as-is (shows Initial Year, total, and currently the Year 1 total contribution)
y1, idx1 = total_and_index_for_yearnum(1)
if show_callouts and (y1 is not None):
    # If you prefer employee-only here too, swap to: init_contrib
    year1_contrib_total = float(df.loc[df["Year"] == 1, "YearlyContrib"].iloc[0])
    callouts.append({
        "x": idx1,
        "y": y1,
        "label": f"Initial Year (Age {int(init_age)})\nContribution: ${year1_contrib_total:,.0f}\nTotal: ${y1:,.0f}"
    })

# 2) Second schedule kicks in — show the **second contribution amount** (employee)
if show_callouts and use_second and int(second_age) >= int(init_age):
    second_year_num = int(second_age) - int(init_age) + 1
    ys, idx2 = total_and_index_for_yearnum(second_year_num)
    if ys is not None:
        second_contrib_employee = float(second_contrib)
        callouts.append({
            "x": idx2,
            "y": ys,
            "label": (
                f"Second Schedule (Age {int(second_age)})\n"
                f"Contribution: ${second_contrib_employee:,.0f}\n"
                f"Total: ${ys:,.0f}"
            )
        })

# 3) Retirement (end of retirement year) — show the **most recent** contribution amount
#    (Second if used in last year, otherwise First)
last_year_num = int(years)  # end of retirement year in your current setup
ylast, idx_last = total_and_index_for_yearnum(last_year_num)
if show_callouts and (ylast is not None):
    # Which schedule applied in the final year? (labeling is start-of-year age)
    last_age_start = int(init_age) + (last_year_num - 1)
    last_employee_contrib = (
        float(second_contrib)
        if (use_second and last_age_start >= int(second_age))
        else float(init_contrib)
    )
    callouts.append({
        "x": idx_last,
        "y": ylast,
        "label": (
            f"Retirement (Age {int(ret_age)})\n"
            f"Contribution: ${last_employee_contrib:,.0f}\n"
            f"Total: ${ylast:,.0f}"
        )
    })

if show_callouts:
    add_callouts_vertical(callouts)

# Render chart
st.pyplot(fig)

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

# ── Export Table (Year 0 EXCLUDED) ────────────────────────────────────────────
try:
    import openpyxl  # noqa: F401
    xlsx_buf = io.BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
        # Export table WITHOUT Year 0 per your requirement
        df_table.to_excel(writer, index=False, sheet_name="Projection")
    xlsx_buf.seek(0)
    st.download_button(
        "📄 Export Table (Excel)",
        data=xlsx_buf.getvalue(),
        file_name="keogh401k_table.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download-table-xlsx",
    )
except Exception:
    csv_data = df_table.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📄 Export Table (CSV)",
        data=csv_data,
        file_name="keogh401k_table.csv",
        mime="text/csv",
        key="download-table-csv",
    )

# ── Data Table (Year 0 EXCLUDED) ─────────────────────────────────────────────
view_cols = [
    "Year", "Age", "AgeStart", "AgeEnd",
    "StartingSavings", "YearlyContrib", "Contributions", "Earnings", "Total"
]
st.dataframe(df_table[view_cols].round(2), use_container_width=True)