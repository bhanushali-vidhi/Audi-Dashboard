import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

st.set_page_config(page_title="Segment III Payout Dashboard", layout="wide")

st.title("Segment III Payout Analytics Dashboard")

# -----------------------------
# DATABASE CONNECTION
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
# SIDEBAR UPLOAD
# -----------------------------

st.sidebar.header("Upload Data")

month = st.sidebar.selectbox(
    "Select Month",
    [
        "January","February","March","April","May","June",
        "July","August","September","October","November","December"
    ]
)

year = st.sidebar.number_input(
    "Select Year",
    min_value=2020,
    max_value=2035,
    value=2024
)

uploaded_file = st.sidebar.file_uploader(
    "Upload Segment III Excel",
    type=["xlsx","xls","xlsb"]
)

# -----------------------------
# PROCESS UPLOADED FILE
# -----------------------------

if uploaded_file:

    df_upload = pd.read_excel(uploaded_file)

    df_upload.columns = (
        df_upload.columns
        .str.strip()
        .str.replace("\n"," ", regex=True)
        .str.replace("  "," ", regex=True)
    )

    # numeric conversions
    if "Final Payout" in df_upload.columns:
        df_upload["Final Payout"] = pd.to_numeric(df_upload["Final Payout"], errors="coerce")

    if "Parts RRP" in df_upload.columns:
        df_upload["Parts RRP"] = pd.to_numeric(df_upload["Parts RRP"], errors="coerce")

    df_upload = df_upload.dropna(subset=["VIN"])

    existing_vins = pd.read_sql("SELECT VIN FROM segment3_data", conn)
    df_upload = df_upload[~df_upload["VIN"].isin(existing_vins["VIN"])]

    # select columns
    db_df = df_upload[[
        "Dealer No_",
        "Dealer name",
        "Region",
        "VIN",
        "Parts RRP",
        "Final Payout",
        "Final Eligibility"
    ]].copy()

    db_df.columns = [
        "Dealer_Code",
        "Dealer_name",
        "Region",
        "VIN",
        "Parts_RRP",
        "Final_Payout",
        "Final_Eligibility"
    ]

    db_df["Month"] = month
    db_df["Year"] = year

    db_df.to_sql(
        "segment3_data",
        conn,
        if_exists="append",
        index=False
    )

    st.sidebar.success(f"{len(db_df)} records uploaded")

# -----------------------------
# LOAD DATA
# -----------------------------

df = pd.read_sql("SELECT * FROM segment3_data", conn)

if df.empty:
    st.warning("Upload a payout Excel to start analytics.")
    st.stop()

# -----------------------------
# FILTERS
# -----------------------------

st.sidebar.header("Filters")

month_filter = st.sidebar.multiselect(
    "Month",
    sorted(df["Month"].dropna().unique())
)

dealer_filter = st.sidebar.multiselect(
    "Dealer",
    sorted(df["Dealer_name"].dropna().unique())
)

region_filter = st.sidebar.multiselect(
    "Region",
    sorted(df["Region"].dropna().unique())
)

if month_filter:
    df = df[df["Month"].isin(month_filter)]

if dealer_filter:
    df = df[df["Dealer_name"].isin(dealer_filter)]

if region_filter:
    df = df[df["Region"].isin(region_filter)]

# -----------------------------
# KPI METRICS
# -----------------------------

st.markdown("<h2 style='text-align:center;'>Key Metrics</h2>", unsafe_allow_html=True)

col1,col2,col3,col4 = st.columns(4)

col1.metric("Total Dealer Payout", f"₹ {df['Final_Payout'].sum():,.0f}")
col2.metric("Total Parts RRP", f"₹ {df['Parts_RRP'].sum():,.0f}")
col3.metric("Total VINs", df["VIN"].nunique())
col4.metric(
    "Eligible VINs",
    df[df["Final_Eligibility"].astype(str).str.lower()=="yes"].shape[0]
)

st.divider()

# -----------------------------
# DEALER LEADERBOARD
# -----------------------------

st.subheader("Dealer Leaderboard")

dealer_leaderboard = df.groupby("Dealer_name").agg(
    Total_Payout=("Final_Payout","sum"),
    Total_VIN=("VIN","nunique"),
    Eligible_VIN=("Final_Eligibility",lambda x: (x.astype(str).str.lower()=="yes").sum())
).reset_index()

dealer_leaderboard["Eligibility %"] = (
    dealer_leaderboard["Eligible_VIN"] /
    dealer_leaderboard["Total_VIN"]
)*100

dealer_leaderboard = dealer_leaderboard.sort_values(
    "Total_Payout",
    ascending=False
).reset_index(drop=True)

dealer_leaderboard.index += 1
dealer_leaderboard.index.name = "Rank"

st.dataframe(dealer_leaderboard, use_container_width=True)

st.divider()

# -----------------------------
# TOP & BOTTOM DEALERS
# -----------------------------

col1,col2 = st.columns(2)

with col1:

    st.subheader("Top 10 Dealers")

    top10 = dealer_leaderboard.head(10)

    fig_top = px.bar(
        top10,
        x="Dealer_name",
        y="Total_Payout",
        text_auto=True
    )

    st.plotly_chart(fig_top, use_container_width=True)

with col2:

    st.subheader("Bottom 10 Dealers")

    bottom10 = dealer_leaderboard.sort_values(
        "Total_Payout",
        ascending=True
    ).head(10)

    fig_bottom = px.bar(
        bottom10,
        x="Dealer_name",
        y="Total_Payout",
        text_auto=True
    )

    st.plotly_chart(fig_bottom, use_container_width=True)

st.divider()

# -----------------------------
# DEALER PAYOUT RANKING
# -----------------------------

st.subheader("Dealer-wise Total Payout")

dealer_payout = df.groupby("Dealer_name")["Final_Payout"].sum().reset_index()

fig_payout = px.bar(
    dealer_payout.sort_values("Final_Payout"),
    x="Final_Payout",
    y="Dealer_name",
    orientation="h"
)

st.plotly_chart(fig_payout, use_container_width=True)

st.divider()

# -----------------------------
# MONTHLY PAYOUT TREND
# -----------------------------

st.subheader("Monthly Payout Trend")

month_order = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

df["Month"] = pd.Categorical(df["Month"], categories=month_order, ordered=True)

monthly_payout = df.groupby(["Year","Month"])["Final_Payout"].sum().reset_index()

fig_trend = px.line(
    monthly_payout,
    x="Month",
    y="Final_Payout",
    color="Year",
    markers=True
)

st.plotly_chart(fig_trend, use_container_width=True)

st.divider()

# -----------------------------
# PARTS RRP VS ELIGIBLE PAYOUT
# -----------------------------

st.subheader("Dealer Comparison: Parts RRP vs Eligible Payout")

eligible_df = df[df["Final_Eligibility"].astype(str).str.lower()=="yes"]

dealer_compare = df.groupby("Dealer_name").agg(
    Parts_RRP=("Parts_RRP","sum")
).reset_index()

eligible_payout = eligible_df.groupby("Dealer_name")["Final_Payout"].sum().reset_index()
eligible_payout.columns = ["Dealer_name","Eligible_Payout"]

dealer_compare = dealer_compare.merge(
    eligible_payout,
    on="Dealer_name",
    how="left"
).fillna(0)

fig_compare = px.bar(
    dealer_compare,
    x="Dealer_name",
    y=["Parts_RRP","Eligible_Payout"],
    barmode="group"
)

st.plotly_chart(fig_compare, use_container_width=True)

# -----------------------------
# RAW DATA
# -----------------------------

with st.expander("View Full Data Table"):
    st.dataframe(df)
