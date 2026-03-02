import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Audi 360° Operations Hub", layout="wide", page_icon="🚗")

# --- STYLING ---
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stMetric { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 10px; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05); 
    }
    </style>
    """, unsafe_allow_html=True)

# --- UTILITY FUNCTIONS ---

def get_col(df, possible_names):
    """
    Scans dataframe columns for a match against a list of possible names.
    """
    cols = {str(c).strip().lower(): c for c in df.columns}
    for name in possible_names:
        if name.lower() in cols:
            return cols[name.lower()]
    return None

def detect_report_type(df):
    """Identifies if the file is LCR, Parts, or Labour based on unique headers."""
    cols = [str(c).strip() for c in df.columns]
    # LCR Detection
    if any("15 Months Retained" in c for c in cols):
        return "LCR"
    # Parts Detection
    if get_col(df, ["Part Number", "Part Description", "COGS", "COGS OLD"]):
        return "Parts"
    # Labour Detection
    if get_col(df, ["Labour Description", "Service Order Type"]):
        return "Labour"
    return None

def clean_data(df):
    """FIXED: Robustly removes 'Total' summary rows."""
    if df.empty: 
        return df
    # Ensure the first column is treated as a string before using .str.strip().upper()
    mask = df.iloc[:, 0].astype(str).str.strip().str.upper() != "TOTAL"
    return df[mask]

# --- MAIN APP ---

st.title("🏁 Audi Dealer Intelligence Dashboard")
st.info("Upload your Excel exports (LCR, Parts, or Labour) to generate analytics.")

uploaded_files = st.file_uploader("Upload Excel File(s)", type=["xlsx"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            # Load and Clean
            raw_df = pd.read_excel(uploaded_file)
            df = clean_data(raw_df)
            report_type = detect_report_type(df)
            
            st.write(f"### 📄 File: {uploaded_file.name}")
            
            if report_type == "LCR":
                st.success("✅ LCR (Retention) Report Detected")
                
                vin_col = get_col(df, ["VIN"])
                ret_col = get_col(df, ["15 Months Retained / Not Retained"])
                dealer_col = get_col(df, ["Last Service Dealer Name"])
                amt_col = get_col(df, ["Amount1"])
                age_col = get_col(df, ["Years Completed for Vehicle sale"])

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total VINs", len(df))
                
                if ret_col:
                    ret_mask = df[ret_col].astype(str).str.contains("Retained", case=False, na=False)
                    ret_rate = ret_mask.mean() * 100
                    m2.metric("Retention Rate", f"{ret_rate:.1f}%")
                
                if amt_col:
                    df[amt_col] = pd.to_numeric(df[amt_col], errors='coerce')
                    m3.metric("Avg Service Spend", f"₹{df[amt_col].mean():,.0f}")
                
                if age_col:
                    m4.metric("Avg Vehicle Age", f"{pd.to_numeric(df[age_col], errors='coerce').mean():.1f} Yrs")

                c1, c2 = st.columns(2)
                with c1:
                    if ret_col:
                        st.plotly_chart(px.pie(df, names=ret_col, hole=0.4, title="Retention Split", 
                                       color_discrete_sequence=["#2ecc71", "#e74c3c"]), use_container_width=True)
                with c2:
                    if dealer_col:
                        top_dealers = df.groupby(dealer_col).size().nlargest(10).reset_index(name='Count')
                        st.plotly_chart(px.bar(top_dealers, x='Count', y=dealer_col, orientation='h', title="Top 10 Service Dealers"), use_container_width=True)

            elif report_type == "Parts":
                st.success("✅ Parts Sales & Inventory Report Detected")
                
                total_col = get_col(df, ["Total", "Total Amount"])
                cogs_col = get_col(df, ["COGS", "COGS OLD"])
                part_desc = get_col(df, ["Part Description"])
                tax_col = get_col(df, ["GST %"])
                part_type = get_col(df, ["Part Type"])

                df[total_col] = pd.to_numeric(df[total_col], errors='coerce').fillna(0)
                df[cogs_col] = pd.to_numeric(df[cogs_col], errors='coerce').fillna(0)
                
                m1, m2, m3 = st.columns(3)
                total_rev = df[total_col].sum()
                m1.metric("Total Revenue", f"₹{total_rev:,.0f}")
                
                margin = ((total_rev - df[cogs_col].sum()) / total_rev) * 100 if total_rev != 0 else 0
                m2.metric("Gross Margin", f"{margin:.1f}%")
                
                if part_desc:
                    m3.metric("Unique Parts Sold", df[part_desc].nunique())

                c1, c2 = st.columns(2)
                with c1:
                    if part_type and part_desc:
                        st.plotly_chart(px.treemap(df, path=[part_type, part_desc], values=total_col, title="Revenue by Part Type"), use_container_width=True)
                with c2:
                    if tax_col:
                        st.plotly_chart(px.pie(df, names=tax_col, values=total_col, title="Revenue by Tax Slab"), use_container_width=True)

            elif report_type == "Labour":
                st.success("✅ Labour Sales Report Detected")
                
                labour_desc = get_col(df, ["Labour Description"])
                total_col = get_col(df, ["Total"])
                date_col = get_col(df, ["Customer Invoice Date", "Invoice Date"])
                qty_col = get_col(df, ["Issue Quantity"])

                df[total_col] = pd.to_numeric(df[total_col], errors='coerce').fillna(0)
                
                # Filter out 'Rounding Off'
                clean_labour_df = df[~df[labour_desc].astype(str).str.contains("Rounding", case=False, na=False)]
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Labour Revenue", f"₹{df[total_col].sum():,.0f}")
                if qty_col:
                    m2.metric("Service Units", f"{pd.to_numeric(df[qty_col], errors='coerce').sum():,.0f}")
                m3.metric("Avg Ticket Size", f"₹{df[total_col].mean():,.0f}")

                c1, c2 = st.columns(2)
                with c1:
                    if labour_desc:
                        top_work = clean_labour_df.groupby(labour_desc)[total_col].sum().nlargest(10).reset_index()
                        st.plotly_chart(px.bar(top_work, x=total_col, y=labour_desc, orientation='h', title="Top 10 Labour Tasks"), use_container_width=True)
                with c2:
                    if date_col:
                        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                        trend = df.groupby(date_col)[total_col].sum().reset_index()
                        st.plotly_chart(px.line(trend, x=date_col, y=total_col, title="Daily Billing Trend"), use_container_width=True)

            else:
                st.error(f"Format not recognized for {uploaded_file.name}.")

            with st.expander(f"🔍 Preview {uploaded_file.name} Data"):
                st.dataframe(df.head(50))
                
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")

else:
    st.warning("Please upload your Audi Excel files (LCR, Parts, or Labour).")