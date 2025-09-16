import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import io
import base64

# ✅ Page config
st.set_page_config(page_title="Keogh/401(k) Projection", layout="wide")

# ── Password gate ─────────────────────────────────────────────────────────────
ALLOWED_PASSWORDS = {"dad1234", "Selevan123"}
password = st.text_input("Enter password to access:", type="password")
if password not in ALLOWED_PASSWORDS:
    st.warning("Please enter the correct password to continue.")
    st.stop()
st.success("Access granted!")

# ── Title and icon ────────────────────────────────────────────────────────────
img_col, title_col = st.columns([0.15, 0.85])
with img_col:
    st.image("Image_2.png", use_container_width=True)
with title_col:
    st.title("Future Value Calculator for Keogh/401(k)")

# ── Sidebar: Theme + Inputs ───────────────────────────────────────────────────
st.sidebar.title("Display & Inputs")

# Projector-friendly theme toggle
theme = st.sidebar.radio(
    "Theme",
    options=["Light (projector-friendly default)", "Dark (high-contrast)"],
    index=0,
    help="Light uses off-white backgrounds to reduce glare on projectors. Dark uses deep gray with bright accents."
)

# Projector-optimized color schemes (labeled)
color_schemes = {
    "Blue & Orange (good for projectors)": ("#377eb8", "#ff7f00"),
    "Teal & Purple (good for projectors)": ("#1b9e77", "#984ea3"),
    "Blue & Gray (good for projectors)": ("#377eb8", "#666666"),
}
selected_scheme = st.sidebar.selectbox("Select Color Scheme", list(color_schemes.keys()))
contrib_color, earnings_color = color_schemes[selected_scheme]

# 401(k) inputs
st.sidebar.subheader("401(k) Inputs")
init_contrib = st.sidebar.number_input("Initial contribution amount (annual)", 1000, 1_000_000, 50_000, 1_000)
init_age = st.sidebar.number_input("Initial Start Age", 18, 80, 35, 1)
second_contrib = st.sidebar.number_input("Second contribution amount (annual)", 1000, 1_000_000, 55_000, 1_000)
second_age = st.sidebar.number_input("Second Start Age", init_age, 80, 50, 1)
employer_match = st.sidebar.number_input("Employer match % (0.00–1.00)", 0.0, 1.0, 0.0, 0.01)
annual_return = st.sidebar.number_input("Annual Return Rate (0.00–0.20)", 0.0, 0.20, 0.06, 0.01)
ret_age = st.sidebar.number_input("Retirement Age", min_value=init_age + 1, max_value=100, value=max(65, init_age + 1), step=1)

frequency = st.sidebar.selectbox("Compounding Frequency", ["biweekly", "monthly", "quarterly"])
periods_per_year = {"biweekly": 26, "monthly": 12, "quarterly": 4}[frequency]
rate_per_period = (1 + annual_return) ** (1 / periods_per_year) - 1

# ── Projection calculation ────────────────────────────────────────────────────
years = int(ret_age - init_age)
total_periods = years * periods_per_year

balance = 0.0
cum_contrib = 0.0
cum_earnings = 0.0
annual_data = []

for period in range(total_periods + 1):
    age = init_age + period / periods_per_year
    contrib = (init_contrib if age < second_age else second_contrib) / periods_per_year
    match = contrib * employer_match
    total_contrib = contrib + match
    earnings = balance * rate_per_period
    balance += total_contrib + earnings
    cum_contrib += total_contrib
    cum_earnings += earnings
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

# ── KPI Metrics ───────────────────────────────────────────────────────────────
end_balance = float(df["Total"].iloc[-1]) if not df.empty else 0.0
end_contrib = float(df["Contributions"].iloc[-1]) if not df.empty else 0.0
end_earnings = float(df["Earnings"].iloc[-1]) if not df.empty else 0.0

col1, col2, col3 = st.columns(3)
col1.metric("💰 Ending Balance", f"${end_balance:,.0f}")
col2.metric("📥 Contributions", f"${end_contrib:,.0f}")
col3.metric("📈 Earnings", f"${end_earnings:,.0f}")

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

# ── Chart ─────────────────────────────────────────────────────────────────────
chart_title = (
    f"Future value calculation for Keogh/401(k)\n"
    f"assuming {annual_return*100:.1f}% return (compounded {frequency}) for {years} years\n"
    f"(For illustrative purposes only)\n"
    f"Starting with ${init_contrib:,.0f}/yr contribution at age {init_age}, "
    f"then ${second_contrib:,.0f}/yr starting at age {second_age} until retirement at age {ret_age}."
)

# Apply text colors for readability
plt.rcParams.update({
    "axes.labelcolor": palette["text"],
    "text.color": palette["text"],
    "xtick.color": palette["text"],
    "ytick.color": palette["text"],
    "axes.titlecolor": palette["text"],
    "axes.edgecolor": palette["spine"],
})

fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor(palette["fig_bg"])
ax.set_facecolor(palette["ax_bg"])

ax.bar(df["Year"], df["Contributions"], color=contrib_color, edgecolor="none", label="Contributions")
ax.bar(df["Year"], df["Earnings"], bottom=df["Contributions"], color=earnings_color, edgecolor="none", label="Earnings")

ax.set_xlabel("Years Worked")
ax.set_ylabel("Amount ($)")
ax.set_title(chart_title, fontsize=11, wrap=True)
leg = ax.legend(frameon=True)
leg.get_frame().set_facecolor(palette["ax_bg"])
leg.get_frame().set_edgecolor(palette["spine"])

# Axes cosmetics for projector visibility
for spine in ax.spines.values():
    spine.set_color(palette["spine"])
ax.set_xticks(df["Year"])
ax.set_xticklabels(df["Year"])
ax.ticklabel_format(style='plain', axis='y')
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
ax.grid(axis='y', linestyle='--', alpha=0.6, color=palette["grid"])

# Annotate ending balance
if not df.empty:
    end_year = int(df["Year"].iloc[-1])
    ax.annotate(
        f"${end_balance:,.0f}",
        xy=(end_year, end_balance),
        xytext=(0, 10),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
        color=palette["text"],
        bbox=dict(boxstyle="round,pad=0.25", fc=palette["annot_fc"], ec=palette["annot_ec"], alpha=0.9)
    )

plt.tight_layout()
st.pyplot(fig)

# ── Export Chart and Table ────────────────────────────────────────────────────
buf = io.BytesIO()
fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight", dpi=200)
buf.seek(0)
img_base64 = base64.b64encode(buf.getvalue()).decode()

col_chart, col_table = st.columns([1, 1])
with col_chart:
    st.markdown(f"""
        <div style="text-align:center; margin-top:10px;">
            <a href="data:image/png;base64,{img_base64}" download="keogh401k_chart.png" style="text-decoration:none;">
                <span style="font-size:20px;">📤 Export Chart</span>
            </a>
        </div>
    """, unsafe_allow_html=True)

with col_table:
    try:
        import openpyxl
        xlsx_buf = io.BytesIO()
        with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Projection")
        xlsx_buf.seek(0)
        st.download_button(
            "📄 Export Table (Excel)",
            data=xlsx_buf.getvalue(),
            file_name="keogh401k_table.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download-table-xlsx-inline",
        )
    except Exception:
        csv_data = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📄 Export Table (CSV)",
            data=csv_data,
            file_name="keogh401k_table.csv",
            mime="text/csv",
            key="download-table-csv-inline",
        )

# ── Data Table ────────────────────────────────────────────────────────────────
view_cols = ["Year", "Age", "Contributions", "Earnings", "Total"]
table_df = df[view_cols].round(2)
st.dataframe(table_df)
