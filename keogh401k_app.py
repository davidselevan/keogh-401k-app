import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import io

# ✅ Page config (must be the first Streamlit call)
st.set_page_config(page_title="Keogh/401(k) Projection", layout="wide")

# ── Password gate with multiple allowed passwords ─────────────────────────────
ALLOWED_PASSWORDS = {"dad1234", "Selevan123"}  # add more as needed

password = st.text_input("Enter password to access:", type="password")
if password not in ALLOWED_PASSWORDS:
    st.warning("Please enter the correct password to continue.")
    st.stop()

st.success("Access granted!")

# ── Title and icon in one row (icon on the LEFT) ─────────────────────────────
img_col, title_col = st.columns([0.15, 0.85])
with img_col:
    # Ensure Image_2.png is in the same folder as this script
    st.image("Image_2.png", use_container_width=True)
with title_col:
    st.title("Future Value Calculator for Keogh/401(k)")

# ── Sidebar inputs ────────────────────────────────────────────────────────────
st.sidebar.title("401(k) Inputs")
init_contrib = st.sidebar.number_input("Initial contribution amount (annual)", 1000, 1_000_000, 50_000, 1_000)
init_age = st.sidebar.number_input("Initial Start Age", 18, 80, 35, 1)
second_contrib = st.sidebar.number_input("Second contribution amount (annual)", 1000, 1_000_000, 55_000, 1_000)
second_age = st.sidebar.number_input("Second Start Age", init_age, 80, 50, 1)
employer_match = st.sidebar.number_input("Employer match %", 0.0, 1.0, 0.0, 0.01)
annual_return = st.sidebar.number_input("Annual Return Rate", 0.0, 0.20, 0.06, 0.01)

# Default to 65 but ensure it's ≥ (init_age + 1) so the widget stays valid
ret_age = st.sidebar.number_input(
    "Retirement Age",
    min_value=init_age + 1,
    max_value=100,
    value=max(65, init_age + 1),
    step=1
)

# ✅ Compounding frequency dropdown (lowercase options + mapping)
frequency = st.sidebar.selectbox("Compounding Frequency", ["biweekly", "monthly", "quarterly"])
periods_per_year = {"biweekly": 26, "monthly": 12, "quarterly": 4}[frequency]
rate_per_period = (1 + annual_return) ** (1 / periods_per_year) - 1

years = int(ret_age - init_age)
total_periods = years * periods_per_year

# ── Projection calculation ────────────────────────────────────────────────────
balance = 0.0
cum_contrib = 0.0
cum_earnings = 0.0
annual_data = []

for period in range(total_periods + 1):
    age = init_age + period / periods_per_year

    # Contributions per period based on age phase
    contrib = (init_contrib if age < second_age else second_contrib) / periods_per_year

    match = contrib * employer_match
    total_contrib = contrib + match

    earnings = balance * rate_per_period
    balance += total_contrib + earnings

    cum_contrib += total_contrib
    cum_earnings += earnings

    # Capture a row at the end of each year
    if period % periods_per_year == 0:
        annual_data.append({
            "Year": int(age - init_age),
            "Age": int(round(age)),
            "Contributions": cum_contrib,
            "Earnings": cum_earnings,
            "Total": balance
        })

df = pd.DataFrame(annual_data)
df = df[df["Year"] <= years]

# ── Stylized KPI Boxes ────────────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)

with k1:
    st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; text-align:center; box-shadow:0 2px 6px rgba(0,0,0,0.1);">
            <h4 style="margin-bottom:10px; color:#333;">Ending Balance</h4>
            <p style="font-size:24px; font-weight:bold; color:#2c7be5;">${end_balance:,.0f}</p>
        </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; text-align:center; box-shadow:0 2px 6px rgba(0,0,0,0.1);">
            <h4 style="margin-bottom:10px; color:#333;">Total Contributions</h4>
            <p style="font-size:24px; font-weight:bold; color:#28a745;">${end_contrib:,.0f}</p>
        </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; text-align:center; box-shadow:0 2px 6px rgba(0,0,0,0.1);">
            <h4 style="margin-bottom:10px; color:#333;">Total Earnings</h4>
            <p style="font-size:24px; font-weight:bold; color:#e83e8c;">${end_earnings:,.0f}</p>
        </div>
    """, unsafe_allow_html=True)


# ── Dynamic chart title (lowercase to match your style) ───────────────────────
chart_title = (
    f"Future value calculation for Keogh/401(k)\n"
    f"assuming {annual_return*100:.1f}% return (compounded {frequency}) for {years} years\n"
    f"(For illustrative purposes only)\n"
    f"Starting with ${init_contrib:,.0f}/yr contribution at age {init_age},\n"
    f"then ${second_contrib:,.0f}/yr starting at age {second_age} until retirement at age {ret_age}."
)

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(df["Year"], df["Contributions"], color="#377eb8", label="Contributions")
ax.bar(df["Year"], df["Earnings"], bottom=df["Contributions"], color="#e41a1c", label="Earnings")

ax.set_xlabel("Years Worked")
ax.set_ylabel("Amount ($)")
ax.set_title(chart_title, fontsize=11, wrap=True)
ax.legend()

# ✅ Force label for each year
ax.set_xticks(df["Year"])  # Show every year label
ax.set_xticklabels(df["Year"])  # Ensure labels match ticks

ax.ticklabel_format(style='plain', axis='y')
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))  # ✅ Dollar formatting

# Subtle horizontal grid lines
ax.grid(axis='y', linestyle='--', alpha=0.4, color='gray')

# ✅ Label the value at the end (annotate the last bar)
if not df.empty:
    end_year = int(df["Year"].iloc[-1])
    ax.annotate(
        f"${end_balance:,.0f}",
        xy=(end_year, end_balance),
        xytext=(0, 8),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
        color="#333",
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85)
    )

plt.tight_layout()
st.pyplot(fig)


# ── Export chart button (PNG) ────────────────────────────────────────────────
buf = io.BytesIO()
fig.savefig(buf, format="png")
st.download_button(
    "Export Chart as PNG",
    buf.getvalue(),
    file_name="keogh401k_chart.png",
    mime="image/png"
)

# ── Show data table ───────────────────────────────────────────────────────────
view_cols = ["Year", "Age", "Contributions", "Earnings", "Total"]
table_df = df[view_cols].round(2)
st.dataframe(table_df)

# ── Download the table (Excel preferred; CSV fallback if openpyxl not present) ─
try:
    import openpyxl  # ensure engine availability
    xlsx_buf = io.BytesIO()
    with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
        table_df.to_excel(writer, index=False, sheet_name="Projection")
    xlsx_buf.seek(0)
    st.download_button(
        "Download Table (Excel)",
        data=xlsx_buf.getvalue(),
        file_name="keogh401k_table.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download-table-xlsx",
    )
except Exception:
    # Graceful fallback to CSV so the user never gets stuck
    csv_data = table_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download Table (CSV)",
        data=csv_data,
        file_name="keogh401k_table.csv",
        mime="text/csv",
        key="download-table-csv",
    )
    st.caption("Excel export unavailable. Add 'openpyxl' to requirements.txt to enable Excel downloads.")
