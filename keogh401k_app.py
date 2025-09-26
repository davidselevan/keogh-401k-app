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

# Fixed-dollar only (percent-of-salary disabled)
contrib_mode = "Fixed Dollar Amount"

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
# Start at day 0 with a Year 0 baseline; compound from day 1 of Year 1 to END of retirement year.
years = int(ret_age - init_age)                 # number of FULL plan years (Year 1..years)
total_periods = years * periods_per_year

balance = float(current_savings)                # starting balance at day 0
cum_contrib = 0.0
cum_earnings = 0.0

annual_data = []                                # Year 0 + end-of-year rows
annual_contrib_for_year = 0.0

employee_contrib_per_period = 0.0
employer_rate_effective = float(employer_contrib_rate)

# ✅ Year 0 baseline row (day 0 snapshot).
annual_data.append({
    "Year": 0,
    "AgeStart": int(init_age),
    "AgeEnd": int(init_age),
    "Age": "",                 # blank for Year 0 (no duplicate "35")
    "AgeLabel": "Start",       # x-axis label
    "StartingSavings": balance,
    "YearlyContrib": 0.0,
    "Contributions": 0.0,
    "Earnings": 0.0,
    "Total": balance
})

for period in range(total_periods):
    year_idx = period // periods_per_year
    pos_in_year = period % periods_per_year
    is_year_start = (pos_in_year == 0)
    is_year_end = (pos_in_year == periods_per_year - 1)

    age_start = int(init_age) + year_idx

    # Set this year's contribution at the START of the year
    if is_year_start:
        contrib_annual = float(second_contrib) if (use_second and age_start >= int(second_age)) else float(init_contrib)
        employee_contrib_per_period = contrib_annual / periods_per_year
        annual_contrib_for_year = 0.0

    # Deposit at start of period, then earn for the period
    employer_amt = employee_contrib_per_period * employer_rate_effective
    total_contrib = employee_contrib_per_period + employer_amt
    balance += total_contrib
    earnings = balance * rate_per_period
    balance += earnings

    # Accumulators
    annual_contrib_for_year += total_contrib
    cum_contrib += total_contrib
    cum_earnings += earnings

    # Capture at END of each plan year
    if is_year_end:
        year_number = year_idx + 1
        age_end = age_start + 1
        annual_data.append({
            "Year": year_number,                     # 1..years
            "AgeStart": int(age_start),
            "AgeEnd": int(age_end),
            "Age": int(age_end),                     # display end-of-year age (Year 1 -> init_age+1)
            "AgeLabel": str(int(age_end)),           # x-axis tick
            "StartingSavings": float(current_savings),
            "YearlyContrib": annual_contrib_for_year,
            "Contributions": cum_contrib,            # cumulative
            "Earnings": cum_earnings,                # cumulative
            "Total": balance                         # end-of-year balance
        })

# Build DataFrame
df = pd.DataFrame(annual_data)

# --- (Optional) quick sanity readout to confirm multiple rows
# st.caption(f"Rows: {len(df)} (should be years+1). Years={years}, Periods={total_periods}")

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

positions = np.arange(len(df))   # 0..N so we always see all bars
bar_width = 0.85

# Draw baseline + stacks
start_band = ax.bar(positions, df["StartingSavings"], color=starting_color, edgecolor="none",
                    label="Starting Savings", zorder=1, width=bar_width)
contrib_band = ax.bar(positions, df["Contributions"], bottom=df["StartingSavings"],
                      color=contrib_color, edgecolor="none", label="Contributions", zorder=2, width=bar_width)
earnings_band = ax.bar(positions, df["Earnings"], bottom=df["StartingSavings"] + df["Contributions"],
                       color=earnings_color, edgecolor="none", label="Earnings", zorder=3, width=bar_width)

# X-axis labels: Year 0 → "Start", then end-of-year ages; last tick == retirement age
ax.set_xticks(positions)
ax.set_xticklabels(df["AgeLabel"], rotation=0)
ax.set_xlabel("End-of-year age (Year 0 = Start)")
ax.set_ylabel("Amount ($)")
ax.set_title("Future Value Calculation", fontsize=11)
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
ax.grid(axis='y', linestyle='--', alpha=0.6)

# Tight x-limits and margins
ax.set_xlim(-0.5, positions[-1] + 0.5)
ax.margins(x=0.02)

# Headroom
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

# ── Helper: y at bar top and x index for a given Year ─────────────────────────
def y_total_and_index_for_year(year_num: int):
    row = df.loc[df["Year"] == int(year_num)]
    if row.empty:
        return None, None
    idx = int(row.index[0])
    return float(row["Total"].iloc[0]), idx

# ── Callouts (use index positions so they align with bars) ────────────────────
def add_callouts_vertical(points):
    if not points:
        return
    height_factor = float(globals().get("callout_height_factor", 0.55))
    text_gap_frac = float(globals().get("callout_text_gap", 0.02))
    min_above_frac = 0.02

    light_mode = ("Light" in theme) if isinstance(theme, str) else True
    box_fc = "#ffffff" if light_mode else "#1b1f24"
    box_ec = "#cfcfcf" if light_mode else "#333333"
    line_color = "#333333"

    ymin, ymax = ax.get_ylim()
    min_above_abs = min_above_frac * ymax
    text_gap_abs = text_gap_frac * ymax

    for p in points:
        x, y_bar = float(p["x"]), float(p["y"])
        y_line_top = y_bar + max(0.18 * ymax, (ymax - y_bar) * height_factor)
        ax.annotate("", xy=(x, y_bar), xytext=(x, y_line_top),
                    arrowprops=dict(arrowstyle="->", lw=1.2, color=line_color), zorder=9)
        y_text = max(y_bar + min_above_abs, y_line_top - text_gap_abs)
        ax.text(x, y_text, p["label"], ha="center", va="top", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.25", fc=box_fc, ec=box_ec), zorder=10)

callouts = []
# End of Year 1
y1, idx1 = y_total_and_index_for_year(1)
if show_callouts and (y1 is not None):
    callouts.append({"x": idx1, "y": y1, "label": f"End of Year 1 (Age {int(init_age)+1})"})

# Second schedule kicks in (first year it applies; end-of-year age)
if show_callouts and use_second and int(second_age) >= int(init_age):
    y2, idx2 = y_total_and_index_for_year(int(second_age) - int(init_age) + 1)
    if y2 is not None:
        callouts.append({"x": idx2, "y": y2, "label": f"Second schedule (Age {int(second_age)+1})"})

# Retirement (end of retirement year)
ylast, idx_last = y_total_and_index_for_year(int(ret_age) - int(init_age))
if show_callouts and (ylast is not None):
    callouts.append({"x": idx_last, "y": ylast, "label": f"Retirement (Age {int(ret_age)})"})

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

# ── Data Table (restored) ─────────────────────────────────────────────────────
view_cols = [
    "Year", "AgeLabel", "Age", "AgeStart", "AgeEnd",
    "StartingSavings", "YearlyContrib", "Contributions", "Earnings", "Total"
]
st.dataframe(df[view_cols].round(2), use_container_width=True)