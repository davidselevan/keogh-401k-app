import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Keogh/401(k) Projection", layout="wide")

st.sidebar.title("401(k) Inputs")
init_contrib = st.sidebar.number_input("Initial contribution amount (annual)", 1000, 1000000, 50000, 1000)
init_age = st.sidebar.number_input("Initial Start Age", 18, 80, 35, 1)
second_contrib = st.sidebar.number_input("Second contribution amount (annual)", 1000, 1000000, 55000, 1000)
second_age = st.sidebar.number_input("Second Start Age", init_age, 80, 50, 1)
employer_match = st.sidebar.number_input("Employer match %", 0.0, 1.0, 0.0, 0.01)
annual_return = st.sidebar.number_input("Annual Return Rate", 0.0, 0.20, 0.06, 0.01)
ret_age = st.sidebar.number_input("Retirement Age", init_age+1, 100, 90, 1)

periods_per_year = 26
biweekly_rate = (1 + annual_return) ** (1/periods_per_year) - 1
years = int(ret_age - init_age)
total_periods = years * periods_per_year

# Projection calculation
balance = 0
cum_contrib = 0
cum_earnings = 0
annual_data = []
for period in range(total_periods + 1):
    age = init_age + period / periods_per_year
    if age < second_age:
        contrib = init_contrib / periods_per_year
    else:
        contrib = second_contrib / periods_per_year
    match = contrib * employer_match
    total_contrib = contrib + match
    earnings = balance * biweekly_rate
    balance += total_contrib + earnings
    cum_contrib += total_contrib
    cum_earnings += earnings
    if period % periods_per_year == 0:
        annual_data.append({
            "Year": int(age - init_age),
            "Age": round(age),
            "Contributions": cum_contrib,
            "Earnings": cum_earnings,
            "Total": balance
        })

df = pd.DataFrame(annual_data)
df = df[df["Year"] <= years]

# Dynamic chart title
chart_title = (
    f"Future Value Calculation for Keogh/401(k)\n"
    f"Assuming {annual_return*100:.1f}% Annual Return (Compounded Biweekly) Over {years} Years\n"
    f"${init_contrib:,.0f}/year at Age {init_age}, then ${second_contrib:,.0f}/year at Age {second_age} until Age {ret_age}\n"
    f"(For Illustrative Purposes Only)"
)




# Plot
fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(df["Year"], df["Contributions"], color="#377eb8", label="Contributions")
ax.bar(df["Year"], df["Earnings"], bottom=df["Contributions"], color="#e41a1c", label="Earnings")
ax.set_xlabel("Years Worked")
ax.set_ylabel("Amount ($)")
ax.set_title(chart_title, fontsize=11, wrap=True)
ax.legend()
ax.set_xticks(np.arange(0, years+1, max(1, years//10)))
ax.ticklabel_format(style='plain', axis='y')
plt.tight_layout()

st.pyplot(fig)

# Export button
import io
buf = io.BytesIO()
fig.savefig(buf, format="png")
st.download_button("Export Chart as PNG", buf.getvalue(), file_name="keogh401k_chart.png", mime="image/png")

st.dataframe(df[["Year", "Age", "Contributions", "Earnings", "Total"]].round(2))
