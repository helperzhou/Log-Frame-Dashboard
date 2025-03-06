import streamlit_highcharts as hct
import streamlit as st
import pandas as pd
import os
import pickle
from datetime import datetime
import io
# ================== CONFIGURE PAGE ==================
st.set_page_config(
    page_title="Intervention Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================== SIDEBAR MENU ==================
with st.sidebar:
    st.title("📊 Navigation")
    menu_option = st.radio("Go to:", ["Dashboard", "Log Frame", "Intervention Tracker"])

# ================== LOAD SAVED DATA ==================
DATA_FILE = "structured_data.pkl"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "rb") as file:
        structured_df = pickle.load(file)
else:
    structured_df = None
    st.error("⚠ No saved data found. Please upload data first.")

# ================== DASHBOARD SECTION ==================
if menu_option == "Dashboard":
    st.title("📊 Intervention Dashboard")

    if structured_df is not None:
        col1, col2 = st.columns(2)

        # Metric 1: Total Interventions
        total_interventions = structured_df["Total Targets"].sum()
        col1.metric(label="📌 Total Interventions", value=f"{total_interventions:,}")

        # Metric 2: Hubs Involved
        hubs = [col for col in structured_df.columns if "Q1 Target" in col]
        num_hubs = len(hubs)
        col2.metric(label="🏢 Hubs Participating", value=num_hubs)

        # ================== VISUALIZATIONS ==================
        st.subheader("📊 Interventions Distribution by Hub")

        # Prepare data for visualization
        hub_totals = structured_df[hubs].sum().reset_index()
        hub_totals.columns = ["Hub", "Total"]
        hub_totals["Hub"] = hub_totals["Hub"].str.replace(" Q1 Target", "")

        # Highcharts Bar Chart - Interventions per Hub
        chart_data = {
            "chart": {"type": "bar"},
            "title": {"text": "Interventions by Hub"},
            "xAxis": {"categories": hub_totals["Hub"].tolist(), "title": {"text": "Hubs"}},
            "yAxis": {"title": {"text": "Total Interventions"}},
            "series": [{"name": "Interventions", "data": hub_totals["Total"].tolist()}]
        }
        hct.streamlit_highcharts(chart_data)

        # ================== PIE CHART - INTERVENTION DISTRIBUTION ==================
        st.subheader("📊 Distribution of Interventions Across Categories")

        section_totals = structured_df.groupby("Output")["Total Targets"].sum().reset_index()

        pie_chart_data = {
            "chart": {"type": "pie"},
            "title": {"text": "Intervention Distribution"},
            "series": [{
                "name": "Total Targets",
                "colorByPoint": True,
                "data": [{"name": row["Output"], "y": row["Total Targets"]} for _, row in section_totals.iterrows()]
            }]
        }
        hct.streamlit_highcharts(pie_chart_data)

# ================== LOG FRAME SECTION ==================
elif menu_option == "Log Frame":
    st.title("📊 Structured Interventions Data Viewer")

    # ==================== Persistent Storage File ====================
    DATA_FILE = "structured_data.pkl"

    # ==================== Load Saved Data ====================
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "rb") as file:
            structured_df = pickle.load(file)
        st.success("✅ Loaded saved dataset from storage!")
    else:
        st.error("❌ No saved dataset found! Please run the initial upload version first.")
        st.stop()

    # ==================== Upload New Actuals Data ====================
    uploaded_file = st.file_uploader("📂 Upload Actual Interventions Data (Excel)", type=["xlsx"])

    if uploaded_file is not None:
        xls = pd.ExcelFile(uploaded_file, engine="openpyxl")

        # Attempt to read the first sheet
        sheet_name = xls.sheet_names[0]
        actuals_df = xls.parse(sheet_name)

        # ==================== Fix Table Formatting Issues ====================

        # Ensure headers are correct (do NOT drop the first row)
        actuals_df.columns = actuals_df.columns.str.strip()  # Remove leading/trailing spaces
        actuals_df = actuals_df.loc[:, ~actuals_df.columns.duplicated()]  # Remove duplicate columns

        # ==================== Handle Missing or Incorrect Column Names ====================
        expected_columns = ["Hub", "Quarter", "Area of Support", "Intervention"]
        missing_columns = [col for col in expected_columns if col not in actuals_df.columns]

        if missing_columns:
            st.error(f"❌ Missing columns in uploaded file: {missing_columns}")
            st.stop()

        # Drop fully empty rows
        actuals_df = actuals_df.dropna(how="all")

        # Convert values to string to prevent issues with NaN values
        actuals_df["Hub"] = actuals_df["Hub"].astype(str).fillna("Unknown")
        actuals_df["Intervention"] = actuals_df["Intervention"].astype(str).fillna("Unknown")

        # ==================== Update Actuals in Structured Data ====================
        for _, row in actuals_df.iterrows():
            hub = row["Hub"]
            quarter = row["Quarter"]
            section = row["Area of Support"]
            intervention = row["Intervention"].strip()

            # Convert intervention format to match structured dataset
            intervention_key = f"Number of SMMEs {intervention.replace('_', ' ')}"

            if hub in structured_df.columns:
                actual_col = f"{hub} {quarter} Actual"

                if actual_col in structured_df.columns:
                    structured_df.loc[
                        (structured_df["Output"] == section) &
                        (structured_df["Intervention"] == intervention_key),
                        actual_col
                    ] += 1  # Increment actual count

        # ==================== Save Updated Data ====================
        with open(DATA_FILE, "wb") as file:
            pickle.dump(structured_df, file)
        st.success("✅ Actuals updated and saved!")

    # ==================== Quarter Selection ====================
    if structured_df is not None:
        quarter_options = ["Q1", "Q2", "Q3", "Q4"]
        selected_quarter = st.selectbox("📅 Select Quarter to View:", quarter_options, index=0)

        # Remove unwanted POE-related columns if they exist
        columns_to_remove = [col for col in structured_df.columns if "POE" in col]
        structured_df = structured_df.drop(columns=columns_to_remove, errors="ignore")

        # Determine which columns to display based on selection
        base_columns = ["Output", "Intervention", "Total Targets"]
        selected_columns = base_columns.copy()

        # Extract hub names dynamically and add relevant columns
        for hub in structured_df.columns[3::9]:  # Extract hub names dynamically
            if hub in structured_df.columns:
                selected_columns.append(hub)  # Always show hub count
                if selected_quarter == "Q1":
                    selected_columns.extend(
                        [col for col in [f"{hub} Q1 Target", f"{hub} Q1 Actual"] if col in structured_df.columns])
                elif selected_quarter == "Q2":
                    selected_columns.extend([col for col in [f"{hub} Q1 Target", f"{hub} Q1 Actual",
                                                             f"{hub} Q2 Target", f"{hub} Q2 Actual"] if
                                             col in structured_df.columns])
                elif selected_quarter == "Q3":
                    selected_columns.extend([col for col in [f"{hub} Q1 Target", f"{hub} Q1 Actual",
                                                             f"{hub} Q2 Target", f"{hub} Q2 Actual",
                                                             f"{hub} Q3 Target", f"{hub} Q3 Actual"] if
                                             col in structured_df.columns])
                elif selected_quarter == "Q4":
                    selected_columns.extend([col for col in [f"{hub} Q1 Target", f"{hub} Q1 Actual",
                                                             f"{hub} Q2 Target", f"{hub} Q2 Actual",
                                                             f"{hub} Q3 Target", f"{hub} Q3 Actual",
                                                             f"{hub} Q4 Target", f"{hub} Q4 Actual"] if
                                             col in structured_df.columns])

        # Ensure only existing columns are selected
        selected_columns = [col for col in selected_columns if col in structured_df.columns]

        # Now safely filter using only the valid columns
        filtered_df = structured_df[selected_columns]

        # ==================== Display Updated Dataset ====================
        st.write(f"### 📋 Structured Dataset with Updated Actuals for {selected_quarter}")
        st.dataframe(filtered_df, use_container_width=True)

        # ==================== Download Updated Data ====================
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            filtered_df.to_excel(writer, index=False, sheet_name="Updated Data")
        processed_data = output.getvalue()

        st.download_button(
            label="📥 Download Updated Data",
            data=processed_data,
            file_name=f"Updated_Structured_Interventions_{selected_quarter}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ================== INTERVENTION TRACKER SECTION ==================
elif menu_option == "Intervention Tracker":
    st.title("✅ Intervention Tracker")
    # ==================== Persistent Storage File ====================
    DATA_FILE = "structured_data.pkl"
    ACTUALS_FILE = "actuals_data.pkl"

    # Load structured data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "rb") as file:
            structured_df = pickle.load(file)
    else:
        st.stop()

    # Load actuals data or create new DataFrame
    if os.path.exists(ACTUALS_FILE):
        with open(ACTUALS_FILE, "rb") as file:
            actuals_df = pickle.load(file)
    else:
        actuals_df = pd.DataFrame(columns=["Enterprise", "Province", "Hub", "Date", "Month", "Quarter",
                                           "Area of Support", "Intervention", "POE", "Consultant 1",
                                           "Consultant 2", "Consultant 3", "Comments"])

    # ==================== Prepopulated Enterprises & Hubs ====================
    enterprise_hub_map = {
        "Mogopogi Adventures": "Rustenburg",
        "Echo Gardens": "Rustenburg",
        "Baking with Mrs Jay": "Polokwane",
        "Dimasisi Projects": "Amandelbult",
        "Cecilian Creatives": "Polokwane",
        "Dingwako Lodge": "Mogalakwena",
        "Lady D Exclusive": "Polokwane",
        "Divine Emporium Holdings": "Mototolo",
        "Boleresmary": "Polokwane",
        "Calvinhos Services": "Polokwane",
        "Chedza Young Professional": "Polokwane",
        "Difokeng Africa": "Polokwane",
        "Food of Joy": "Mototolo",
        "Frandmolf Enterprise": "Amandelbult",
        "Jaagbaan Lodge Capital": "Mogalakwena",
        "Keitsile General Trading": "Polokwane",
        "Kele Pheko Trading Ldge": "Mogalakwena",
        "Lapizi Trading": "Mototolo",
        "Lesoslo Lodge": "Mototolo",
        "Mahlaka A Gwato": "Twickenham",
        "Maitekamantle": "Amandelbult",
        "Makhegy Trading": "Polokwane",
        "Mmamoleshe Enterprise Trading": "Rustenburg",
        "Mars Lifestyle Tradng": "Mototolo",
        "Mashabela Business Enterprise": "Mototolo",
        "Mashlee Capital": "Mototolo",
        "Mega kruz Holdings Trading": "Polokwane",
        "Mehlcho ta Arghas": "Mototolo",
        "Marakeng Tours": "Amandelbult",
        "MNM Guesthouse": "Polokwane",
        "Magopodi Adventures": "Rustenburg",
        "Mokonyane Creatives": "Mogalakwena",
        "Mlebo Art Worx Creatives": "Twickenham",
        "Molma Lodge": "Mototolo",
        "Mokore Bakery Confectionary": "Twickenham",
        "Mothubesa Trading": "Mogalakwena",
        "Motse Rive Guesthouse": "Twickenham",
        "Nare ya Kgotso": "Twickenham",
        "Oak Sprint": "Amandelbult",
        "Ompile and Relebogile": "Mogalakwena",
        "Peoleung conservation": "Rustenburg",
        "Petty Travel and Tours": "Mototolo",
        "Refeneo Travels and Tours": "Rustenburg",
        "Regorogile": "Amandelbult",
        "Sechabelo Trading and Project Capital": "Polokwane",
        "Sematheki": "Polokwane",
        "Shatadikethu Enterprise": "Amandelbult",
        "Sisykn Solutions": "Polokwane",
        "Stee56 Travel": "Mototolo",
        "Tibi In Trans": "Twickenham",
        "Tigrani Mix Guesthouse": "Polokwane",
        "Zimasa Travel": "Rustenburg"
    }

    # Extract Hubs and Provinces
    hubs = list(set(enterprise_hub_map.values()))
    hub_province_map = {
        "Rustenburg": "North West",
        "Polokwane": "Limpopo",
        "Amandelbult": "Limpopo",
        "Mogalakwena": "Limpopo",
        "Mototolo": "Limpopo",
        "Twickenham": "Limpopo"
    }

    # Extract Sections and Interventions from Structured Data
    sections = structured_df["Output"].unique().tolist()
    interventions = structured_df["Intervention"].unique().tolist()
    cleaned_interventions = [x.replace("Number of SMMEs ", "") for x in interventions]


    # ==================== Capture Form ====================
    with st.form("intervention_form"):
        st.subheader("📋 Add New Intervention Entry")
        enterprise = st.selectbox("🏢 Enterprise", list(enterprise_hub_map.keys()))

        # Create empty placeholders for dynamic hub and province updates
        hub_placeholder = st.empty()
        province_placeholder = st.empty()

        # Update hub and province dynamically
        hub = enterprise_hub_map.get(enterprise, "Unknown")
        province = hub_province_map.get(hub, "Unknown")

        # Display dynamic values in placeholders
        hub_placeholder.text(f"📍 Hub: {hub}")
        province_placeholder.text(f"🌍 Province: {province}")

        area_of_support = st.selectbox("📖 Area of Support", sections)
        intervention = st.selectbox("🛠️ Intervention", cleaned_interventions)

        # Text Boxes for Additional Information

        poe = st.text_input("📄 POE Number")
        col1, col2 = st.columns([20,1])
        with col1:
            consultant1 = st.text_input("👨‍💼 Consultant 1")
            consultant2 = st.text_input("👩‍💼 Consultant 2")
            consultant3 = st.text_input("👩‍💼 Consultant 3")
        comment = st.text_area("📝 Comments")

        # Auto-fill Date & Quarter
        today = datetime.today()
        date_str = today.strftime("%d-%b-%y")  # Format as "5-Oct-24"
        month_str = today.strftime("%B")  # "October"
        quarter_map = {1: "Q1", 2: "Q1", 3: "Q1",
                       4: "Q2", 5: "Q2", 6: "Q2",
                       7: "Q3", 8: "Q3", 9: "Q3",
                       10: "Q4", 11: "Q4", 12: "Q4"}
        quarter_str = quarter_map[today.month]

        st.write(f"📅 Date: {date_str}, 📆 Month: {month_str}, 🔢 Quarter: {quarter_str}")

        submit_button = st.form_submit_button("✅ Submit Entry")

    # ==================== Process Submission ====================
    if submit_button:
        # Get quarter dynamically
        today = datetime.today()
        quarter_map = {1: "Q1", 2: "Q1", 3: "Q1", 4: "Q2", 5: "Q2", 6: "Q2", 7: "Q3", 8: "Q3", 9: "Q3", 10: "Q4",
                       11: "Q4", 12: "Q4"}
        quarter_str = quarter_map[today.month]

        # Update Log Frame (Increment Actuals)
        intervention_key = f"Number of SMMEs {intervention}"
        actual_col = f"{hub} {quarter_str} Actual"

        if actual_col in structured_df.columns:
            structured_df.loc[
                (structured_df["Output"] == area_of_support) &
                (structured_df["Intervention"] == intervention_key),
                actual_col
            ] += 1

        # Save Updated Log Frame
        with open(DATA_FILE, "wb") as file:
            pickle.dump(structured_df, file)

        new_entry = pd.DataFrame([{
            "Enterprise": enterprise,
            "Province": province,
            "Hub": hub,
            "Date": date_str,
            "Month": month_str,
            "Quarter": quarter_str,
            "Area of Support": area_of_support,
            "Intervention": intervention,
            "POE": poe,
            "Consultant 1": consultant1,
            "Consultant 2": consultant2,
            "Consultant 3": consultant3,
            "Comments": comment
        }])

        actuals_df = pd.concat([actuals_df, new_entry], ignore_index=True)

        # Save updated actuals
        with open(ACTUALS_FILE, "wb") as file:
            pickle.dump(actuals_df, file)

        st.success("✅ Entry successfully saved!")

    st.write("### 📋 Captured Intervention Entries")
    st.dataframe(actuals_df, use_container_width=True)

