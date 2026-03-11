import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from thefuzz import process, fuzz

# -----------------------------
# LUXURY UI CONFIG
# -----------------------------
st.set_page_config(page_title="Audi Segment III Analytics", layout="wide", initial_sidebar_state="expanded")

# Custom Audi-themed CSS
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #0e1117;
        color: #f5f5f5;
    }
    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 600 !important;
        color: #f5f5f5 !important;
    }
    div[data-testid="metric-container"] {
        background-color: #1a1c23;
        border: 1px solid #333;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    /* Headers */
    h1, h2, h3 {
        color: #ffffff !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        letter-spacing: 1px;
    }
    /* Sidebar */
    .css-1d391kg {
        background-color: #16181d !important;
    }
    /* Buttons */
    .stButton>button {
        background-color: #bb0a30 !important; /* Audi Red */
        color: white !important;
        border-radius: 5px;
        border: none;
        width: 100%;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #ff1a4a !important;
        box-shadow: 0 0 10px rgba(187, 10, 48, 0.5);
    }
    /* Dataframes */
    .stDataFrame {
        border: 1px solid #333;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# -----------------------------
# DATABASE CONNECTION
# -----------------------------
conn = sqlite3.connect("analytics.db", check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS segment3_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Dealer_Code TEXT,
    Dealer_name TEXT,
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
# SMART COLUMN MAPPING
# -----------------------------
TARGET_COLUMNS = {
    "Dealer_Code": ["dealer no", "dlr code", "dealer_id", "dealer number", "dlr_no"],
    "Dealer_name": ["dealer name", "dlr name", "outlet name", "dealer_name"],
    "VIN": ["vin", "chassis number", "chassis no", "serial number"],
    "Parts_RRP": ["parts rrp", "rrp", "parts price", "mrp"],
    "Final_Payout": ["final payout", "payout", "incentive", "total payout"],
    "Final_Eligibility": ["final eligibility", "eligible", "status", "eligibility"]
}

def get_smart_mapping(upload_cols):
    mapping = {}
    actual_cols = [str(c).strip() for c in upload_cols]
    for target, variations in TARGET_COLUMNS.items():
        match, score = process.extractOne(target, actual_cols, scorer=fuzz.token_sort_ratio)
        if score > 70: mapping[target] = match
    return mapping

# -----------------------------
# SIDEBAR: DATA CONTROLS
# -----------------------------
with st.sidebar:
    st.image("https://www.audi.com/content/dam/gbp2/experience-audi/brand-and-identity/rings/audi_rings_desktop.png", width=100)
    st.title("Data Control")
    
    month_list = ["January","February","March","April","May","June","July","August","September","October","November","December"]
    
    with st.expander("📂 Import New Dataset"):
        up_m = st.selectbox("Month", month_list)
        up_y = st.number_input("Year", 2024, 2030, 2024)
        uploaded_file = st.file_uploader("Upload Excel", type=["xlsx","xlsb"])
        
        if uploaded_file:
            df_upload = pd.read_excel(uploaded_file)
            mapping = get_smart_mapping(df_upload.columns)
            
            if len(mapping) < 6:
                st.error("Header mismatch detected.")
            else:
                db_df = df_upload[[mapping[k] for k in TARGET_COLUMNS.keys()]].copy()
                db_df.columns = list(TARGET_COLUMNS.keys())
                
                # Cleanup
                db_df["Final_Payout"] = pd.to_numeric(db_df["Final_Payout"], errors="coerce").fillna(0)
                db_df["Parts_RRP"] = pd.to_numeric(db_df["Parts_RRP"], errors="coerce").fillna(0)
                db_df["VIN"] = db_df["VIN"].astype(str).str.strip().upper()
                db_df["Final_Eligibility"] = db_df["Final_Eligibility"].astype(str).str.strip().lower()
                db_df["Month"], db_df["Year"] = up_m, up_y

                if st.button("Confirm & Sync"):
                    db_df.to_sql("segment3_data", conn, if_exists="append", index=False)
                    st.success("Synced to Cloud.")
                    st.rerun()

    with st.expander("🗑️ Database Maintenance"):
        del_m = st.selectbox("Month to Clear", month_list)
        del_y = st.number_input("Year to Clear", 2024, 2030, 2024)
        if st.button("Delete Selected Records"):
            cursor.execute("DELETE FROM segment3_data WHERE Month=? AND Year=?", (del_m, del_y))
            conn.commit()
            st.rerun()

# -----------------------------
# MAIN DASHBOARD
# -----------------------------
df = pd.read_sql("SELECT * FROM segment3_data", conn)

if df.empty:
    st.warning("Awaiting Data Upload...")
    st.stop()

# Filters
st.sidebar.divider()
st.sidebar.header("Analytics Filters")
f_dealer = st.sidebar.multiselect("Dealer Network", sorted(df["Dealer_name"].unique()))
f_month = st.sidebar.multiselect("Timeframe", month_list)

if f_dealer: df = df[df["Dealer_name"].isin(f_dealer)]
if f_month: df = df[df["Month"].isin(f_month)]

# --- METRIC SECTION ---
st.markdown("### Executive Overview")
m1, m2, m3, m4 = st.columns(4)

total_pay = df["Final_Payout"].sum()
unique_vins = df["VIN"].nunique()
eligible_vins = df[df["Final_Eligibility"] == "yes"]["VIN"].nunique()
rate = (eligible_vins/unique_vins*100) if unique_vins > 0 else 0

m1.metric("Gross Payout", f"₹ {total_pay:,.0f}")
m2.metric("Total VIN Assets", f"{unique_vins:,}")
m3.metric("Eligible Units", f"{eligible_vins:,}")
m4.metric("Eligibility Rate", f"{rate:.1f}%")

st.divider()

# --- ANALYTICS SECTION ---
c_left, c_right = st.columns([6, 4])

with c_left:
    st.markdown("### Performance Leaderboard")
    leaderboard = df.groupby("Dealer_name").agg({
        "Final_Payout": "sum",
        "VIN": "nunique"
    }).rename(columns={"VIN": "Unique_VINs"}).sort_values("Final_Payout", ascending=False).reset_index()
    
    st.dataframe(
        leaderboard.style.format({"Final_Payout": "₹{:,.0f}"})
        .background_gradient(subset=["Final_Payout"], cmap="Reds"),
        use_container_width=True, height=400
    )

with c_right:
    st.markdown("### Payout Concentration")
    fig = px.pie(leaderboard.head(5), values='Final_Payout', names='Dealer_name', 
                 hole=.6, color_discrete_sequence=px.colors.sequential.Reds_r)
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                      font_color="white", margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

# --- CHART SECTION ---
st.markdown("### Monthly Payout Trend")
trend_df = df.groupby(["Year", "Month"])["Final_Payout"].sum().reset_index()
fig_trend = px.area(trend_df, x="Month", y="Final_Payout", line_shape="spline", 
                    color_discrete_sequence=['#bb0a30'])
fig_trend.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                        font_color="white", xaxis_gridcolor='#333', yaxis_gridcolor='#333')
st.plotly_chart(fig_trend, use_container_width=True)

# Raw Data
with st.expander("📂 Open Transaction Ledger"):
    st.dataframe(df, use_container_width=True)
