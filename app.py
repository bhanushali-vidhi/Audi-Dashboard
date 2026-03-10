import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Excel Analytics Dashboard", layout="wide")

st.title("Excel Analytics Dashboard")

# -------------------------------
# Function: make duplicate columns unique
# -------------------------------
def make_unique(columns):
    seen = {}
    new_cols = []
    for col in columns:
        if col in seen:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            new_cols.append(col)
    return new_cols


# -------------------------------
# Upload Excel
# -------------------------------
uploaded_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx", "xls", "xlsm", "xlsb"]
)

# -------------------------------
# Month Year Selection
# -------------------------------
col1, col2 = st.columns(2)

month = col1.selectbox(
    "Select Month",
    [
        "January","February","March","April",
        "May","June","July","August",
        "September","October","November","December"
    ]
)

year = col2.selectbox(
    "Select Year",
    list(range(2020,2035))
)

# -------------------------------
# Process Excel
# -------------------------------
if uploaded_file:

    df = pd.read_excel(uploaded_file)

    # Clean column names
    df.columns = df.columns.astype(str).str.replace("\n"," ").str.strip()

    # Remove empty columns
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    # Fix duplicate column names
    df.columns = make_unique(df.columns)

    # Remove fully empty rows
    df = df.dropna(how="all")

    st.success(f"Loaded {len(df)} rows for {month} {year}")

    # -------------------------------
    # Sidebar Filters
    # -------------------------------
    st.sidebar.header("Filters")

    filtered_df = df.copy()

    # Dealer filter
    if "Dealer name" in df.columns:
        dealers = st.sidebar.multiselect(
            "Dealer",
            df["Dealer name"].dropna().unique(),
            default=df["Dealer name"].dropna().unique()
        )
        filtered_df = filtered_df[filtered_df["Dealer name"].isin(dealers)]

    # Region filter
    if "Region" in df.columns:
        regions = st.sidebar.multiselect(
            "Region",
            df["Region"].dropna().unique(),
            default=df["Region"].dropna().unique()
        )
        filtered_df = filtered_df[filtered_df["Region"].isin(regions)]

    # VIN search
    if "VIN" in df.columns:
        vin_search = st.sidebar.text_input("Search VIN")
        if vin_search:
            filtered_df = filtered_df[
                filtered_df["VIN"].astype(str).str.contains(vin_search)
            ]

    # Model filter
    if "Vehicle Model  Desc" in df.columns:
        models = st.sidebar.multiselect(
            "Vehicle Model",
            df["Vehicle Model  Desc"].dropna().unique(),
            default=df["Vehicle Model  Desc"].dropna().unique()
        )
        filtered_df = filtered_df[
            filtered_df["Vehicle Model  Desc"].isin(models)
        ]

    # -------------------------------
    # KPI Metrics
    # -------------------------------
    st.subheader("Key Metrics")

    col1, col2, col3 = st.columns(3)

    if "Amount" in filtered_df.columns:
        col1.metric(
            "Total Amount",
            f"{filtered_df['Amount'].sum():,.2f}"
        )

    if "Dealer name" in filtered_df.columns:
        col2.metric(
            "Total Dealers",
            filtered_df["Dealer name"].nunique()
        )

    col3.metric(
        "Total Records",
        len(filtered_df)
    )

    st.divider()

    # -------------------------------
    # Charts
    # -------------------------------

    col1, col2 = st.columns(2)

    # Dealer Revenue
    if "Dealer name" in filtered_df.columns and "Amount" in filtered_df.columns:

        dealer_data = (
            filtered_df.groupby("Dealer name")["Amount"]
            .sum()
            .sort_values(ascending=False)
            .head(15)
            .reset_index()
        )

        fig1 = px.bar(
            dealer_data,
            x="Dealer name",
            y="Amount",
            title="Top Dealers by Amount"
        )

        col1.plotly_chart(fig1, use_container_width=True)

    # Region Revenue
    if "Region" in filtered_df.columns and "Amount" in filtered_df.columns:

        region_data = (
            filtered_df.groupby("Region")["Amount"]
            .sum()
            .reset_index()
        )

        fig2 = px.pie(
            region_data,
            names="Region",
            values="Amount",
            title="Region Contribution"
        )

        col2.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    # Vehicle Model
    if "Vehicle Model  Desc" in filtered_df.columns:

        model_data = (
            filtered_df["Vehicle Model  Desc"]
            .value_counts()
            .head(10)
            .reset_index()
        )

        model_data.columns = ["Model","Count"]

        fig3 = px.bar(
            model_data,
            x="Model",
            y="Count",
            title="Top Vehicle Models"
        )

        col3.plotly_chart(fig3, use_container_width=True)

    # Invoice Distribution
    if "Part Type" in filtered_df.columns:

        part_data = (
            filtered_df["Part Type"]
            .value_counts()
            .reset_index()
        )

        part_data.columns = ["Part Type","Count"]

        fig4 = px.pie(
            part_data,
            names="Part Type",
            values="Count",
            title="Part Type Distribution"
        )

        col4.plotly_chart(fig4, use_container_width=True)

    st.divider()

    # -------------------------------
    # Data Table
    # -------------------------------
    st.subheader("Filtered Data")

    st.dataframe(
        filtered_df,
        use_container_width=True
    )

else:
    st.info("Upload an Excel file to start the dashboard.")
