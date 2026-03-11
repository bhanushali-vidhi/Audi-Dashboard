import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Audi Dealer Analytics",
    page_icon="🚗",
    layout="wide"
)

# -----------------------------
# AUDI STYLE
# -----------------------------
st.markdown("""
<style>

/* App background */
.stApp {
    background-color:#0A0A0A;
    color:white;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color:#111111;
}

/* Headers */
h1,h2,h3,h4 {
    color:#E5002B;
}

/* Metric cards */
[data-testid="metric-container"] {
    background-color:#1A1A1A;
    border:1px solid #E5002B;
    padding:15px;
    border-radius:10px;
}

/* Tables */
.stDataFrame {
    background-color:#111111;
}

/* Buttons */
.stButton>button {
    background-color:#E5002B;
    color:white;
    border-radius:8px;
}

/* Divider */
hr {
    border:1px solid #333333;
}

</style>
""", unsafe_allow_html=True)

# -----------------------------
# COLORS
# -----------------------------
AUDI_RED = "#E5002B"
AUDI_BG = "#0A0A0A"
AUDI_COLORS = ["#E5002B","#FFFFFF","#888888","#444444"]

# -----------------------------
# HEADER
# -----------------------------
st.markdown(
"""
<h1 style='text-align:center'>AUDI Dealer Performance Analytics</h1>
<center style='color:grey'>Segment III Incentive Dashboard</center>
""",
unsafe_allow_html=True
)

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
# SIDEBAR UPLOAD
# -----------------------------
st.sidebar.header("Upload Excel")

month = st.sidebar.selectbox(
"Month",
["January","February","March","April","May","June",
"July","August","September","October","November","December"]
)

year = st.sidebar.number_input("Year",2020,2035,2024)

uploaded_file = st.sidebar.file_uploader(
"Upload Segment III Excel",
type=["xlsx","xls", "xlsm", "xlsb"]
)

# -----------------------------
# PROCESS UPLOAD
# -----------------------------
if uploaded_file is not None:

    # Get file extension
    file_type = uploaded_file.name.split(".")[-1].lower()

    # Read based on file type
    if file_type == "xlsb":
        df_upload = pd.read_excel(uploaded_file, engine="pyxlsb")

    elif file_type == "xls":
        df_upload = pd.read_excel(uploaded_file, engine="xlrd")

    else:  # xlsx, xlsm etc
        df_upload = pd.read_excel(uploaded_file, engine="openpyxl")

    df_upload.columns = (
        df_upload.columns.astype(str)
        .str.replace("\n"," ")
        .str.replace("_"," ")
        .str.strip()
    )

    # -----------------------------
    # REMOVE TOTAL ROWS
    # -----------------------------
    df_upload = df_upload[
        ~df_upload.astype(str).apply(
            lambda row: row.str.contains("total", case=False, na=False)
        ).any(axis=1)
    ]

    df_upload = df_upload.loc[:,~df_upload.columns.duplicated()]

    df_upload["VIN"] = df_upload["VIN"].astype(str).str.upper().str.strip()

    df_upload["Final Payout"] = pd.to_numeric(
        df_upload["Final Payout"],errors="coerce"
    )

    df_upload["Parts RRP"] = pd.to_numeric(
        df_upload["Parts RRP"],errors="coerce"
    )

    db_df = df_upload[
        [
        "Dealer No",
        "Dealer name",
        "Region",
        "VIN",
        "Parts RRP",
        "Final Payout",
        "Final Eligibility"
        ]
    ].copy()

    db_df.columns=[
    "Dealer_Code",
    "Dealer_name",
    "Region",
    "VIN",
    "Parts_RRP",
    "Final_Payout",
    "Final_Eligibility"
    ]

    db_df["Month"]=month
    db_df["Year"]=year

    db_df.to_sql(
        "segment3_data",
        conn,
        if_exists="append",
        index=False
    )

    st.sidebar.success(f"{len(db_df)} rows uploaded")

# -----------------------------
# LOAD DATA
# -----------------------------
df = pd.read_sql("SELECT * FROM segment3_data",conn)

if df.empty:
    st.warning("Upload Excel to start analytics")
    st.stop()

df["Final_Eligibility"]=(
df["Final_Eligibility"]
.astype(str)
.str.lower()
.str.strip()
)

# -----------------------------
# FILTERS
# -----------------------------
st.sidebar.header("Filters")

region_filter = st.sidebar.multiselect(
"Region",
sorted(df["Region"].dropna().unique())
)

dealer_filter = st.sidebar.multiselect(
"Dealer",
sorted(df["Dealer_name"].dropna().unique())
)

month_filter = st.sidebar.multiselect(
"Month",
sorted(df["Month"].dropna().unique())
)

if region_filter:
    df=df[df["Region"].isin(region_filter)]

if dealer_filter:
    df=df[df["Dealer_name"].isin(dealer_filter)]

if month_filter:
    df=df[df["Month"].isin(month_filter)]

# -----------------------------
# KPI METRICS
# -----------------------------
total_vins = df["VIN"].nunique()

eligible_vins = df[
df["Final_Eligibility"]=="yes"
]["VIN"].nunique()

eligibility_rate = (
eligible_vins/total_vins*100
if total_vins>0 else 0
)

st.markdown("## Key Metrics")

c1,c2,c3,c4,c5 = st.columns(5)

c1.metric("Total Dealer Payout",f"₹ {df['Final_Payout'].sum():,.0f}")
c2.metric("Total Parts RRP",f"₹ {df['Parts_RRP'].sum():,.0f}")
c3.metric("Total VINs",total_vins)
c4.metric("Eligible VINs",eligible_vins)
c5.metric("Eligibility Rate",f"{eligibility_rate:.1f}%")

st.markdown("<hr>",unsafe_allow_html=True)

# -----------------------------
# DEALER LEADERBOARD
# -----------------------------
st.markdown("## 🏆 Dealer Leaderboard")

dealer = df.groupby("Dealer_name").agg(
Total_Payout=("Final_Payout","sum"),
Total_VIN=("VIN","nunique"),
Eligible_VIN=("VIN",
lambda x: x[df.loc[x.index,"Final_Eligibility"]=="yes"].nunique())
).reset_index()

dealer["Eligibility %"]=dealer["Eligible_VIN"]/dealer["Total_VIN"]*100

dealer=dealer.sort_values(
"Total_Payout",ascending=False
).reset_index(drop=True)

dealer["Rank"]=dealer.index+1

def medal(x):
    return "🥇" if x==1 else "🥈" if x==2 else "🥉" if x==3 else ""

dealer["🏆"]=dealer["Rank"].apply(medal)

dealer=dealer[
["🏆","Rank","Dealer_name","Total_Payout","Total_VIN","Eligible_VIN","Eligibility %"]
]

st.dataframe(
dealer.style.format({
"Total_Payout":"₹ {:,.0f}",
"Eligibility %":"{:.1f}%"
}),
use_container_width=True
)

st.markdown("<hr>",unsafe_allow_html=True)

# -----------------------------
# MONTHLY TREND
# -----------------------------
st.markdown("## Monthly Payout Trend")

trend=df.groupby("Month")["Final_Payout"].sum().reset_index()

fig=px.line(
trend,
x="Month",
y="Final_Payout",
markers=True,
color_discrete_sequence=[AUDI_RED]
)

fig.update_layout(
plot_bgcolor=AUDI_BG,
paper_bgcolor=AUDI_BG,
font_color="white"
)

st.plotly_chart(fig,use_container_width=True)

# -----------------------------
# REGION PERFORMANCE
# -----------------------------
st.markdown("## Region Performance")

region=df.groupby("Region")["Final_Payout"].sum().reset_index()

fig=px.bar(
region,
x="Region",
y="Final_Payout",
color_discrete_sequence=AUDI_COLORS
)

fig.update_layout(
plot_bgcolor=AUDI_BG,
paper_bgcolor=AUDI_BG,
font_color="white"
)

st.plotly_chart(fig,use_container_width=True)

# -----------------------------
# DEALER PAYOUT
# -----------------------------
st.markdown("## Dealer Payout")

dealer_chart=df.groupby(
"Dealer_name"
)["Final_Payout"].sum().reset_index()

fig=px.bar(
dealer_chart.sort_values("Final_Payout"),
x="Final_Payout",
y="Dealer_name",
orientation="h",
color_discrete_sequence=[AUDI_RED]
)

fig.update_layout(
plot_bgcolor=AUDI_BG,
paper_bgcolor=AUDI_BG,
font_color="white"
)

st.plotly_chart(fig,use_container_width=True)

# -----------------------------
# PARTS VS PAYOUT
# -----------------------------
st.markdown("## Parts RRP vs Eligible Payout")

eligible_df=df[df["Final_Eligibility"]=="yes"]

parts=df.groupby("Dealer_name")["Parts_RRP"].sum().reset_index()

payout=eligible_df.groupby(
"Dealer_name"
)["Final_Payout"].sum().reset_index()

payout.columns=["Dealer_name","Eligible_Payout"]

compare=parts.merge(payout,on="Dealer_name",how="left").fillna(0)

fig=px.bar(
compare,
x="Dealer_name",
y=["Parts_RRP","Eligible_Payout"],
barmode="group",
color_discrete_sequence=AUDI_COLORS
)

fig.update_layout(
plot_bgcolor=AUDI_BG,
paper_bgcolor=AUDI_BG,
font_color="white"
)

st.plotly_chart(fig,use_container_width=True)

# -----------------------------
# HEATMAP
# -----------------------------
st.markdown("## Eligibility Heatmap (Region vs Month)")

heat=df.groupby(
["Region","Month"]
).agg(
Eligible=("VIN",
lambda x: x[df.loc[x.index,"Final_Eligibility"]=="yes"].nunique())
).reset_index()

heatmap=heat.pivot(
index="Region",
columns="Month",
values="Eligible"
)

fig=px.imshow(
heatmap,
color_continuous_scale="Reds",
aspect="auto"
)

fig.update_layout(
plot_bgcolor=AUDI_BG,
paper_bgcolor=AUDI_BG,
font_color="white"
)

st.plotly_chart(fig,use_container_width=True)

# -----------------------------
# RAW DATA
# -----------------------------
with st.expander("View Raw Data"):
    st.dataframe(df)
