import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import io

# ✅ Page config (must be the first Streamlit call)
st.set_page_config(page_title="Keogh/401(k) Projection", layout="wide")

# ── Title and icon ────────────────────────────────────────────────────────────
img_col, title_col = st.columns([0.15, 0.85])
with img_col:
    # If you want to use Image_2.png instead, just change the file name here
    st.image("Image_3.png", use_container_width=True)
with title_col:
    st.title("Future Value Calculator for Keogh/401(k)")

# ── Sidebar: Theme + Inputs ───────────────────────────────────────────────────
st.sidebar.title("Display & Inputs")

# Theme toggle (projector aware)
theme = st.sidebar.radio(
    "Theme",
    options=["Light (projector-friendly default)", "Dark (high-contrast)"],
    index=0,
    help="Light uses off-white backgrounds to reduce glare on projectors. Dark uses deep gray with bright accents.",
    key="theme_mode",
)

# Color scheme presets
color_schemes = {
    # Original sets
    "Blues": ("#377eb8", "#4daf4a"),
    "Grays": ("#999999", "#666666"),
    "Red & Blue": ("#e41a1c", "#377eb8"),
    "Purples": ("#984ea3", "#7570b3"),
    "Orange & Teal": ("#ff7f00", "#1b9e77"),
    # Projector-optimized sets
    "Blue & Orange (good for projectors)": ("#377eb8", "#ff7f00"),
    "Teal & Purple (good for projectors)": ("#1b9e77", "#984ea3"),
    "Blue & Gray (good for projectors)": ("#377eb8", "#666666"),
}
selected_scheme = st.sidebar.selectbox(
    "Select Color Scheme",
    list(color_schemes.keys()),
    key="color_scheme",
)
contrib_color, earnings_color = color_schemes[selected_scheme]

# 401(k) inputs
st.sidebar.subheader("401(k) Inputs")
init_contrib = st.sidebar.number_input(
    "Initial contribution amount (annual)", 1000, 1_000_000, 50_000, 1_000, key="init_contrib"
)
init_age = st.sidebar.number_input("Initial Start Age", 18, 80, 35, 1, key="init_age")
second_contrib = st.sidebar.number_input(
    "Second contribution amount (annual)", 1000, 1_000_000, 55_000, 1_000, key="second_contrib"
)
second_age = st.sidebar.number_input("Second Start Age", init_age, 80, 50, 1, key="second_age")
employer_match = st.sidebar.number_input(
    "Employer match % (0.00–1.00)", 0.0, 1.0, 0.0, 0.01, key="employer_match"
)
annual_return = st.sidebar.number_input(
    "Annual Return Rate (0.00–0.20)", 0.0, 0.20, 0.06, 0.01, key="annual_return"
)
ret_age = st.sidebar.number_input(
    "Retirement Age",
    min_value=int(init_age) + 1,
    max_value=100,
    value=max(65, int(init_age) + 1),
    step=1,
    key="ret_age",
)
frequency = st.sidebar.selectbox(
    "Compounding Frequency", ["biweekly", "monthly", "quarterly"], key="comp_freq"
)
periods_per_year = {"biweekly": 26, "monthly": 12, "quarterly": 4}[frequency]
rate_per_period = (1 + annual_return) ** (1 / periods_per_year) - 1

# Guardrail: Second Start Age must be >= Initial Start Age
if second_age < init_age:
    st.error("Second Start Age cannot be before Initial Start Age. Please adjust in the sidebar.")
    st.stop()

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

    # capture at whole-year boundaries
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

# Apply text/axis colors for readability *before* plotting
plt.rcParams.update({
    "axes.labelcolor": palette["text"],
    "text.color": palette["text"],
    "xtick.color": palette["text"],
    "ytick.color": palette["text"],
    "axes.titlecolor": palette["text"],
    "axes.edgecolor": palette["spine"],
})

# ── Chart ─────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor(palette["fig_bg"])
ax.set_facecolor(palette["ax_bg"])

# Stacked bars
ax.bar(df["Year"], df["Contributions"], color=contrib_color, edgecolor="none", label="Contributions")
ax.bar(df["Year"], df["Earnings"], bottom=df["Contributions"], color=earnings_color, edgecolor="none", label="Earnings")

# Labels and grid
ax.set_xlabel("Years Worked")
ax.set_ylabel("Amount ($)")
ax.set_title("Future Value Calculation", fontsize=11)
ax.legend(frameon=True)
ax.ticklabel_format(style='plain', axis='y')
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('${x:,.0f}'))
ax.grid(axis='y', linestyle='--', alpha=0.6, color=palette["grid"])

# ── Add Annotations for Key Ages (Age + Total only) ───────────────────────────
def add_arrow_for_age(target_age: int, label: str):
    row = df.loc[df["Age"] == int(target_age)]
    if row.empty:
        return
    x = int(row["Year"].iloc[0])
    total = float(row["Total"].iloc[0])

    ax.annotate(
        f"{label}\nAge: {target_age}\nTotal: ${total:,.0f}",
        xy=(x, total),                # point to top of stacked bar
        xytext=(0, 24),               # place text slightly above the point
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=9,
        color=palette["text"],
        bbox=dict(boxstyle="round,pad=0.3", fc=palette["annot_fc"], ec=palette["annot_ec"]),
        arrowprops=dict(arrowstyle="->", color=palette["text"], lw=1)
    )

# De-duplicate in case ages overlap
seen = set()
for age, label in [
    (int(init_age), "Initial Start"),
    (int(second_age), "Second Start"),
    (int(ret_age), "Retirement")
]:
    if age not in seen:
        add_arrow_for_age(age, label)
        seen.add(age)

# ❌ Removed the ending balance annotation per your request

plt.tight_layout()

# ── Export Chart (PNG) — button above the chart ───────────────────────────────
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

# Caption under chart
st.caption("Created by David Selevan")

# ── Export Table ──────────────────────────────────────────────────────────────
# Try Excel; if engine not present in runtime, fall back to CSV
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
view_cols = ["Year", "Age", "Contributions", "Earnings", "Total"]
st.dataframe(df[view_cols].round(2))