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

# ── Inputs ────────────────────────────────────────────────────────────────────
st.sidebar.subheader("401(k) Inputs")

current_savings = st.sidebar.number_input("Current Savings (Year 0)", 0.0, 10_000_000.0, 0.0, 1_000.0)
use_second = st.sidebar.checkbox("Use second contribution schedule", value=True)

# 🔹 Contribution Mode Toggle — COMMENTED OUT
# contrib_mode = st.sidebar.radio("Contribution Mode", ["Fixed Dollar Amount", "Percent of Salary"], index=0)
contrib_mode = "Fixed Dollar Amount"

init_contrib = st.sidebar.number_input("Initial contribution amount (annual)", 1000, 1_000_000, 50_000, 1_000)
init_age = st.sidebar.number_input("Initial Start Age", 18, 80, 35, 1)

second_contrib = st.sidebar.number_input("Second contribution amount (annual)", 1000, 1_000_000, 55_000, 1_000)
second_age_default = max(50, int(init_age))
second_age = st.sidebar.number_input("Second Start Age", int(init_age), 80, second_age_default, 1)

# Percent-of-salary inputs — COMMENTED OUT
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

employer_contrib_rate = st.sidebar.number_input("Employer contribution % (0.00–1.00)", 0.0, 1.0, 0.0, 0.01)
annual_return = st.sidebar.number_input("Annual Return Rate (0.00–0.20)", 0.0, 0.20, 0.06, 0.01)
ret_age = st.sidebar.number_input("Retirement Age", int(init_age) + 1, 100, max(65, int(init_age) + 1), 1)
frequency = st.sidebar.selectbox("Compounding Frequency", ["biweekly", "monthly", "quarterly"])
periods_per_year = {"biweekly": 26, "monthly": 12, "quarterly": 4}[frequency]
rate_per_period = (1 + annual_return) ** (1 / periods_per_year) - 1

# ── Projection calculation ────────────────────────────────────────────────────
years = int(ret_age - init_age)
total_periods = years * periods_per_year

balance = float(current_savings)
cum_contrib = 0.0
cum_earnings = 0.0
annual_data = []
annual_contrib_for_year = 0.0

employee_contrib_per_period = 0.0
employer_rate_effective = float(employer_contrib_rate)

for period in range(total_periods + 1):
    year_idx = period // periods_per_year
    age_plan_year = int(init_age) + year_idx
    is_year_start = (period % periods_per_year == 0)

    if is_year_start:
        if period > 0:
            annual_data[-1]["YearlyContrib"] = annual_contrib_for_year
        annual_contrib_for_year = 0.0

        if use_second and age_plan_year >= int(second_age):
            contrib_annual = float(second_contrib)
        else:
            contrib_annual = float(init_contrib)

        employee_annual_final = contrib_annual
        employee_contrib_per_period = employee_annual_final / periods_per_year

        annual_data.append({
            "Year": int(age_plan_year - int(init_age)),
            "Age": int(age_plan_year),
            "StartingSavings": float(current_savings),
            "Contributions": cum_contrib,
            "Earnings": cum_earnings,
            "Total": balance
        })

    employer_amt = employee_contrib_per_period * employer_rate_effective
    total_contrib = employee_contrib_per_period + employer_amt
    annual_contrib_for_year += total_contrib

    # ✅ Contributions at start of period
    balance += total_contrib
    earnings = balance * rate_per_period
    balance += earnings

    cum_contrib += total_contrib
    cum_earnings += earnings

if annual_data:
    annual_data[-1]["YearlyContrib"] = annual_contrib_for_year

df = pd.DataFrame(annual_data)
df = df[df["Year"] <= years]

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

bottoms = np.zeros(len(df))
if current_savings > 0:
    ax.bar(df["Year"], df["StartingSavings"], color=starting_color, label="Starting Savings", zorder=1)
    bottoms = df["StartingSavings"].values

ax.bar(df["Year"], df["Contributions"], bottom=bottoms, color=contrib_color, label="Contributions", zorder=2)
ax.bar(df["Year"], df["Earnings"], bottom=bottoms + df["Contributions"], color=earnings_color, label="Earnings", zorder=3)

ax.set_xlabel("Years Worked")
ax.set_ylabel("Amount ($)")
ax.set_title("Future Value Calculation", fontsize=11)
ax.legend(frameon=True)
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
ax.grid(axis='y', linestyle='--', alpha=0.6)

plt.tight_layout()
st.pyplot(fig)

# ── Export Table ──────────────────────────────────────────────────────────────
try:
    import openpyxl
    xlsx_buf = io.BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Projection")
    xlsx_buf.seek(0)
    st.download_button("📄 Export Table (Excel)", data=xlsx_buf.getvalue(), file_name="keogh401k_table.xlsx")
except Exception:
    csv_data = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📄 Export Table (CSV)", data=csv_data, file_name="keogh401k_table.csv")

# ── Data Table ────────────────────────────────────────────────────────────────
view_cols = ["Year", "Age"] + (["StartingSavings"] if current_savings > 0 else []) + ["YearlyContrib", "Contributions", "Earnings", "Total"]
st.dataframe(df[view_cols].round(2), use_container_width=True)