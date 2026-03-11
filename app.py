import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

st.set_page_config(page_title="Audi Segment III Dashboard", layout="wide")

# -----------------------------
# AUDI THEME
# -----------------------------

st.markdown("""
<style>

.stApp {
    background-color:#0a0a0a;
    color:white;
}

h1,h2,h3,h4 {
    color:#e31235;
}

[data-testid="metric-container"] {
    background-color:#1c1c1c;
    border-radius:10px;
    padding:15px;
}

</style>
""", unsafe_allow_html=True)

st.title("Audi Segment III Payout Analytics Dashboard")

# -----------------------------
# DATABASE
# -----------------------------

conn = sqlite3.connect("analytics.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS segment3_data (
id INTEGER PRIMARY KEY AUTOINCREMENT,
Dealer_Code TEXT,
Dealer_name TEXT,
Region TEXT,
VIN TEXT,
Parts_RRP REAL,
Final_Payout REAL,
Final_Eligibility TEXT,
Month TEXT,
Year INTEGER,
upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

# -----------------------------
# SIDEBAR
# -----------------------------

st.sidebar.header("Upload Data")

month = st.sidebar.selectbox(
"Month",
[
"January","February","March","April","May","June",
"July","August","September","October","November","December"
]
)

year = st.sidebar.number_input(
"Year",
min_value=2020,
max_value=2035,
value=2024
)

uploaded_file = st.sidebar.file_uploader(
"Upload Excel",
type=["xlsx","xls","xlsm","xlsb"]
)

# -----------------------------
# FILE PROCESSING
# -----------------------------

if uploaded_file is not None:

    file_type = uploaded_file.name.split(".")[-1].lower()

    if file_type == "xlsb":
        df_upload = pd.read_excel(uploaded_file, engine="pyxlsb")

    elif file_type == "xls":
        df_upload = pd.read_excel(uploaded_file, engine="xlrd")

    else:
        df_upload = pd.read_excel(uploaded_file, engine="openpyxl")

    # -----------------------------
    # CLEAN COLUMN NAMES
    # -----------------------------

    df_upload.columns = (
        df_upload.columns
        .str.strip()
        .str.replace("\n"," ", regex=True)
        .str.replace("  "," ", regex=True)
    )

    # -----------------------------
    # REMOVE TOTAL ROWS
    # -----------------------------

    df_upload = df_upload[
        ~df_upload.astype(str).apply(
            lambda row: row.str.contains("total", case=False, na=False)
        ).any(axis=1)
    ]

    # -----------------------------
    # SMART COLUMN DETECTION
    # -----------------------------

    column_map = {}

    for col in df_upload.columns:

        c = col.lower()

        if "dealer" in c and "name" in c:
            column_map[col] = "Dealer_name"

        elif "dealer" in c and ("code" in c or "no" in c):
            column_map[col] = "Dealer_Code"

        elif "region" in c:
            column_map[col] = "Region"

        elif "vin" in c:
            column_map[col] = "VIN"

        elif "rrp" in c:
            column_map[col] = "Parts_RRP"

        elif "payout" in c:
            column_map[col] = "Final_Payout"

        elif "eligibility" in c:
            column_map[col] = "Final_Eligibility"

    df_upload.rename(columns=column_map, inplace=True)

    # -----------------------------
    # REQUIRED COLUMNS CHECK
    # -----------------------------

    required_cols = [
        "Dealer_Code",
        "Dealer_name",
        "VIN",
        "Parts_RRP",
        "Final_Payout",
        "Final_Eligibility"
    ]

    missing = [c for c in required_cols if c not in df_upload.columns]

    if missing:
        st.error(f"Missing columns: {missing}")
        st.stop()

    # -----------------------------
    # NUMERIC CONVERSION
    # -----------------------------

    df_upload["Parts_RRP"] = pd.to_numeric(df_upload["Parts_RRP"], errors="coerce")
    df_upload["Final_Payout"] = pd.to_numeric(df_upload["Final_Payout"], errors="coerce")

    # -----------------------------
    # REMOVE EMPTY VIN
    # -----------------------------

    df_upload = df_upload.dropna(subset=["VIN"])

    # -----------------------------
    # ADD MONTH YEAR
    # -----------------------------

    df_upload["Month"] = month
    df_upload["Year"] = year

    # -----------------------------
    # SAVE TO DATABASE
    # -----------------------------

    df_upload.to_sql(
        "segment3_data",
        conn,
        if_exists="append",
        index=False
    )

    st.sidebar.success(f"{len(df_upload)} records uploaded")

# -----------------------------
# LOAD DATA
# -----------------------------

df = pd.read_sql("SELECT * FROM segment3_data", conn)

if df.empty:
    st.warning("Upload Excel to start analytics")
    st.stop()

# -----------------------------
# FILTERS
# -----------------------------

st.sidebar.header("Filters")

dealer_filter = st.sidebar.multiselect(
"Dealer",
sorted(df["Dealer_name"].dropna().unique())
)

month_filter = st.sidebar.multiselect(
"Month",
sorted(df["Month"].dropna().unique())
)

if "Region" in df.columns:

    region_filter = st.sidebar.multiselect(
    "Region",
    sorted(df["Region"].dropna().unique())
    )

    if region_filter:
        df = df[df["Region"].isin(region_filter)]

if dealer_filter:
    df = df[df["Dealer_name"].isin(dealer_filter)]

if month_filter:
    df = df[df["Month"].isin(month_filter)]

# -----------------------------
# KPI METRICS
# -----------------------------

st.subheader("Key Metrics")

col1,col2,col3,col4,col5 = st.columns(5)

total_payout = df["Final_Payout"].sum()
total_rrp = df["Parts_RRP"].sum()

total_vins = df["VIN"].nunique()

eligible_vins = df[
df["Final_Eligibility"].astype(str).str.strip().str.lower()=="yes"
]["VIN"].nunique()

eligibility_rate = (eligible_vins/total_vins)*100 if total_vins else 0

col1.metric("Total Dealer Payout", f"₹ {total_payout:,.0f}")
col2.metric("Total Parts RRP", f"₹ {total_rrp:,.0f}")
col3.metric("Total VINs", total_vins)
col4.metric("Eligible VINs", eligible_vins)
col5.metric("Eligibility Rate", f"{eligibility_rate:.1f}%")

st.divider()

# -----------------------------
# DEALER LEADERBOARD
# -----------------------------

st.subheader("Dealer Leaderboard")

dealer_leaderboard = df.groupby("Dealer_name").agg(
Total_Payout=("Final_Payout","sum"),
Total_VIN=("VIN","nunique"),
Eligible_VIN=("Final_Eligibility",lambda x:(x.astype(str).str.lower()=="yes").sum())
).reset_index()

dealer_leaderboard["Eligibility %"] = (
dealer_leaderboard["Eligible_VIN"] /
dealer_leaderboard["Total_VIN"]
)*100

dealer_leaderboard = dealer_leaderboard.sort_values(
"Total_Payout",
ascending=False
)

st.dataframe(
dealer_leaderboard.style.format({
"Total_Payout":"₹ {:,.0f}",
"Eligibility %":"{:.1f}%"
})
)

st.divider()

# -----------------------------
# TOP / BOTTOM DEALERS
# -----------------------------

col1,col2 = st.columns(2)

top10 = dealer_leaderboard.head(10)

fig1 = px.bar(
top10,
x="Dealer_name",
y="Total_Payout",
color="Total_Payout",
color_continuous_scale="reds"
)

col1.plotly_chart(fig1, use_container_width=True)

bottom10 = dealer_leaderboard.sort_values(
"Total_Payout"
).head(10)

fig2 = px.bar(
bottom10,
x="Dealer_name",
y="Total_Payout",
color="Total_Payout",
color_continuous_scale="reds"
)

col2.plotly_chart(fig2, use_container_width=True)

st.divider()

# -----------------------------
# DEALER PAYOUT GRAPH
# -----------------------------

dealer_payout = df.groupby("Dealer_name")["Final_Payout"].sum().reset_index()

fig3 = px.bar(
dealer_payout.sort_values("Final_Payout"),
x="Final_Payout",
y="Dealer_name",
orientation="h",
color="Final_Payout",
color_continuous_scale="reds"
)

st.plotly_chart(fig3, use_container_width=True)

st.divider()

# -----------------------------
# RRP vs PAYOUT
# -----------------------------

eligible_df = df[
df["Final_Eligibility"].astype(str).str.lower()=="yes"
]

dealer_compare = df.groupby("Dealer_name").agg(
Parts_RRP=("Parts_RRP","sum")
).reset_index()

eligible_payout = eligible_df.groupby("Dealer_name")["Final_Payout"].sum().reset_index()

eligible_payout.columns=["Dealer_name","Eligible_Payout"]

dealer_compare = dealer_compare.merge(
eligible_payout,
on="Dealer_name",
how="left"
).fillna(0)

fig4 = px.bar(
dealer_compare,
x="Dealer_name",
y=["Parts_RRP","Eligible_Payout"],
barmode="group"
)

st.plotly_chart(fig4, use_container_width=True)

# -----------------------------
# RAW DATA
# -----------------------------

with st.expander("View Full Data"):
    st.dataframe(df)

if st.sidebar.button("Reset Database"):
    cursor.execute("DELETE FROM segment3_data")
    conn.commit()
    st.success("Database Reset")
