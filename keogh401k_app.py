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

# ── 401(k) inputs ────────────────────────────────────────────────────────────
st.sidebar.subheader("401(k) Inputs")

current_savings = st.sidebar.number_input(
    "Current Savings (Year 0)",
    min_value=0.0, max_value=10_000_000.0, value=0.0, step=1_000.0
)

use_second = st.sidebar.checkbox("Use second contribution schedule", value=True)

init_contrib = st.sidebar.number_input("Initial contribution amount (annual)", 1000, 1_000_000, 50_000, 1_000)
init_age = st.sidebar.number_input("Initial Start Age", 18, 80, 35, 1)

second_contrib = st.sidebar.number_input("Second contribution amount (annual)", 1000, 1_000_000, 55_000, 1_000)
second_age_default = max(50, int(init_age))
second_age = st.sidebar.number_input("Second Start Age", int(init_age), 80, second_age_default, 1)

employer_contrib_rate = st.sidebar.number_input("Employer contribution % (0.00–1.00)", 0.0, 1.0, 0.0, 0.01)
annual_return = st.sidebar.number_input("Annual Return Rate (0.00–0.20)", 0.0, 0.20, 0.06, 0.01)

ret_age = st.sidebar.number_input(
    "Retirement Age", min_value=int(init_age) + 1, max_value=100, value=max(65, int(init_age) + 1), step=1
)

frequency = st.sidebar.selectbox("Compounding Frequency", ["biweekly", "monthly", "quarterly"])
periods_per_year = {"biweekly": 26, "monthly": 12, "quarterly": 4}[frequency]
rate_per_period = (1 + annual_return) ** (1 / periods_per_year) - 1

if use_second and second_age < init_age:
    st.error("Second Start Age cannot be before Initial Start Age.")
    st.stop()

# ── Projection calculation ────────────────────────────────────────────────────
years = int(ret_age - init_age)
total_periods = years * periods_per_year

balance = float(current_savings)
cum_contrib = 0.0
cum_earnings = 0.0
annual_data = []

# ✅ Year 0 baseline row
annual_data.append({
    "Year": 0,
    "Age": "",
    "AgeEnd": int(init_age),
    "StartingSavings": float(current_savings),
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

    if is_year_start:
        contrib_annual = float(second_contrib if use_second and age_start >= int(second_age) else init_contrib)
        employee_contrib_per_period = contrib_annual / periods_per_year
        annual_contrib_for_year = 0.0

    employer_amt = employee_contrib_per_period * employer_contrib_rate
    total_contrib = employee_contrib_per_period + employer_amt

    balance += total_contrib
    earnings = balance * rate_per_period
    balance += earnings

    annual_contrib_for_year += total_contrib
    cum_contrib += total_contrib
    cum_earnings += earnings

    if is_year_end:
        annual_data.append({
            "Year": year_idx + 1,
            "Age": int(age_start),
            "AgeEnd": int(age_start + 1),
            "StartingSavings": float(current_savings),
            "YearlyContrib": annual_contrib_for_year,
            "Contributions": cum_contrib,
            "Earnings": cum_earnings,
            "Total": balance
        })

df = pd.DataFrame(annual_data)

# ── KPI Metrics ───────────────────────────────────────────────────────────────
end_balance = float(df["Total"].iloc[-1])
end_contrib = float(df["Contributions"].iloc[-1])
end_earnings = float(df["Earnings"].iloc[-1])

col1, col2, col3 = st.columns(3)
col1.metric("💰 Ending Balance", f"${end_balance:,.0f}")
col2.metric("📥 Contributions (incl. employer)", f"${end_contrib:,.0f}")
col3.metric("📈 Earnings", f"${end_earnings:,.0f}")

# ── Chart ─────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor("#f7f7f7" if "Light" in theme else "#111418")
ax.set_facecolor("#ffffff" if "Light" in theme else "#0c0f13")

years_x = df["Year"]
ax.bar(years_x, df["StartingSavings"], color=starting_color, edgecolor="none", label="Starting Savings", zorder=1)
ax.bar(years_x, df["Contributions"], bottom=df["StartingSavings"], color=contrib_color, edgecolor="none", label="Contributions", zorder=2)
ax.bar(years_x, df["Earnings"], bottom=df["StartingSavings"] + df["Contributions"], color=earnings_color, edgecolor="none", label="Earnings", zorder=3)

ax.set_xlabel("Year (0 = starting point)")
ax.set_ylabel("Amount ($)")
ax.set_title("Future Value Calculation", fontsize=11)
ax.legend(frameon=True)
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
ax.grid(axis='y', linestyle='--', alpha=0.6)

# Headroom
max_total = float(df["Total"].max())
ax.set_ylim(top=max_total * 1.28)

# ── Callouts ──────────────────────────────────────────────────────────────────
def y_total_at_year(year_num):
    row = df.loc[df["Year"] == int(year_num)]
    return None if row.empty else float(row["Total"].iloc[0])

callouts = []
y0 = y_total_at_year(0)
if y0 is not None:
    callouts.append({"x": 0, "y": y0, "label": f"Starting Savings\nYear 0 | Age: {int(init_age)}\nTotal: ${y0:,.0f}"})
if use_second and int(second_age) >= int(init_age):
    second_year_num = int(second_age) - int(init_age) + 1
    ys = y_total_at_year(second_year_num)
    if ys is not None:
        callouts.append({"x": second_year_num, "y": ys, "label": f"Second Contribution Starts\nYear {second_year_num} | Age: {int(second_age)}\nTotal: ${ys:,.0f}"})
last_year_num = int(years)
yr = y_total_at_year(last_year_num)
if yr is not None:
    callouts.append({"x": last_year_num, "y": yr, "label": f"Retirement\nYear {last_year_num} | Age: {int(ret_age)}\nTotal: ${yr:,.0f}"})

for i, p in enumerate(callouts):
    ax.annotate(p["label"], xy=(p["x"], p["y"]), xytext=(p["x"] + (-0.9 if i % 2 == 0 else 0.9), p["y"] * 1.1),
                textcoords="data", arrowprops=dict(facecolor="black", arrowstyle="->", lw=1),
                fontsize=9, ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.3", fc="#ffffff" if "Light" in theme else "#1b1f24", ec="#cfcfcf" if "Light" in theme else "#333333"))

plt.tight_layout()

# ✅ Export Chart
png_buf = io.BytesIO()
fig.savefig(png_buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight", dpi=200)
png_buf.seek(0)
st.download_button("📷 Export Chart (PNG)", data=png_buf.getvalue(), file_name="keogh401k_chart.png", mime="image/png")

st.pyplot(fig)

# ── Export Table ──────────────────────────────────────────────────────────────
xlsx_buf = io.BytesIO()
with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="Projection")
xlsx_buf.seek(0)
st.download_button("📄 Export Table (Excel)", data=xlsx_buf.getvalue(), file_name="keogh401k_table.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ── Data Table ────────────────────────────────────────────────────────────────
view_cols = ["Year", "Age", "StartingSavings", "YearlyContrib", "Contributions", "Earnings", "Total"]
st.dataframe(df[view_cols].round(2), use_container_width=True)
