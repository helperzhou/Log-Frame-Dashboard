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

# ================== USER AUTHENTICATION ==================
USER_CREDENTIALS = {
    "helperzhou@gmail.com": {"password": "Helper123", "role": "admin"},
    "shirley@sigmaintl.co.za": {"password": "Shirley123", "role": "user"},
}

# Initialize session state for authentication and role
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.role = None
    st.session_state.username = None

# Login Page
def login():
    st.title("🔒 Login to Intervention Dashboard")

    # Use temporary variables for inputs
    input_username = st.text_input("👤 Username", key="login_username")
    input_password = st.text_input("🔑 Password", type="password", key="login_password")

    if st.button("Login"):
        if input_username in USER_CREDENTIALS and USER_CREDENTIALS[input_username]["password"] == input_password:
            st.session_state.authenticated = True
            st.session_state.role = USER_CREDENTIALS[input_username]["role"]
            st.session_state.username = input_username  # Only set this after login
            st.success(f"✅ Login successful! Welcome, {input_username}. Redirecting...")
            st.rerun()
        else:
            st.error("❌ Incorrect username or password.")

# Logout Function
def logout():
    st.session_state.authenticated = False
    st.session_state.role = None
    st.session_state.username = None
    st.rerun()

# Check authentication
if not st.session_state.authenticated:
    login()
    st.stop()


# ================== LOAD SAVED DATA ==================
DATA_FILE = "structured_data.pkl"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "rb") as file:
        structured_df = pickle.load(file)
else:
    structured_df = None
    st.error("⚠ No saved data found. Please upload data first.")

if st.session_state.role == "admin":
    # ================== SIDEBAR MENU ==================
    with st.sidebar:
        st.title("📊 Navigation")
        menu_option = st.radio("Go to:", ["Dashboard", "Log Frame", "Intervention Tracker"])
        st.button("🚪 Logout", on_click=logout)

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

            # ================== FIX COLUMN NAMES ==================
            structured_df.columns = structured_df.columns.str.strip()  # Remove extra spaces

            # Identify the correct hub column names from the structured dataframe
            hub_names = ["Rustenburg", "Polokwane", "Amandelbult", "Mogalakwena", "Mototolo", "Twickenham"]

            # Ensure only existing hub columns are selected
            valid_hub_columns = [col for col in hub_names if col in structured_df.columns]

            # Compute total interventions per hub using actual data
            hub_totals_corrected = structured_df[valid_hub_columns].sum().reset_index()
            hub_totals_corrected.columns = ["Hub", "Total"]

            # Display dataframe for verification
            st.subheader("📊 Interventions Distribution by Hub")

            # Highcharts Horizontal Bar Chart - Interventions per Hub
            chart_data = {
                "chart": {"type": "bar"},
                "title": {"text": "Interventions by Hub"},
                "xAxis": {"categories": hub_totals_corrected["Hub"].tolist(), "title": {"text": "Hubs"}},
                "yAxis": {"title": {"text": "Total Interventions"}},
                "series": [{"name": "Interventions", "data": hub_totals_corrected["Total"].tolist()}],
                "plotOptions": {
                    "bar": {
                        "horizontal": True  # Ensures the bar chart is horizontal
                    }
                }
            }

            # Render the chart using Streamlit Highcharts
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
            st.error("❌ Structured data file not found. Please upload data first.")
            st.stop()

        # Load actuals data or create new DataFrame
        if os.path.exists(ACTUALS_FILE):
            with open(ACTUALS_FILE, "rb") as file:
                actuals_df = pickle.load(file)
        else:
            actuals_df = pd.DataFrame(columns=["Enterprise", "Province", "Hub", "Date", "Month", "Quarter",
                                               "Area of Support", "Intervention", "POE", "Consultant 1",
                                               "Consultant 2", "Consultant 3", "Comments"])

        # ==================== Enterprise to Hub Mapping ====================
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

        hub_province_map = {
            "Rustenburg": "North West",
            "Polokwane": "Limpopo",
            "Amandelbult": "Limpopo",
            "Mogalakwena": "Limpopo",
            "Mototolo": "Limpopo",
            "Twickenham": "Limpopo"
        }

        enterprise_data = {
            "Mogopogi Adventures": {
                "Marketing & Sales": [
                    "Website Development & Domain Email Reg",
                    "Social Media Page Setup",
                    "Marketing Plan",
                ],
                "Business & Financial Management": [
                    "Management Accounts",
                    "Record Keeping and Management",
                ],
                "Mentorship & Training": [
                    "Financial Literacy Mentoring",
                    "Marketing Mentoring",
                    "Executive Mentoring",
                ],
            },
            "Echo Gardens": {
                "Marketing & Sales": [
                    "Website Hosting",
                    "Business Cards",
                    "Pamphlets & Brochures",
                ],
                "Business & Financial Management": [
                    "Regulatory Compliance (VAT, UIF, COIDA Registration)",
                    "Risk Management Plan",
                ],
            },
            "Baking with Mrs Jay": {
                "Marketing & Sales": [
                    "Company Profile",
                    "Email Signature",
                    "Branded Banner",
                ],
                "Business & Financial Management": [
                    "Business Funding Proposal",
                    "Funding Linkages",
                    "Insurance Tips Webinar",
                ],
                "Mentorship & Training": [
                    "Strategic Plan",
                    "Business Communication (How to Pitch)",
                ],
            },
            "Dimasisi Projects": {
                "Marketing & Sales": [
                    "Industry Membership",
                    "Marketing Linkages Time",
                    "Other Marketing Support",
                ],
                "Business & Financial Management": [
                    "CRM Solutions Linkages",
                    "Linkages with Chef",
                ],
            },
            "Cecilian Creatives": {
                "Marketing & Sales": [
                    "Company Profile",
                    "Branded Banner",
                    "Business Cards",
                ],
                "Technology & Digital Support": [
                    "Digital Transformation",
                    "Excel Skills Training",
                ],
            },
            "Dingwako Lodge": {
                "Marketing & Sales": [
                    "Pamphlets & Brochures",
                    "Website Hosting",
                ],
                "Training & Mentorship": [
                    "Industry Training (Courses)",
                    "Financial Literacy Mentoring",
                    "Fireside Chat",
                ],
            },
            "Lady D Exclusive": {
                "Marketing & Sales": [
                    "Website Development & Domain Email Reg",
                    "Social Media Page Setup",
                ],
                "Financial Management & Compliance": [
                    "Risk Management Plan",
                    "Business Operations Plan",
                ],
            },
            "Divine Emporium Holdings": {
                "Marketing & Sales": [
                    "Other Marketing Support",
                    "Marketing Plan",
                ],
                "Technology & Digital Support": [
                    "Technology Application Support",
                    "Growth Plan",
                ],
            },
            "Boleresmary": {
                "Marketing & Sales": [
                    "Branded Banner",
                    "Business Cards",
                ],
                "Business & Financial Management": [
                    "Regulatory Compliance",
                    "Financial Literacy Mentoring",
                ],
            },
            "Calvinhos Services": {
                "Marketing & Sales": [
                    "Company Profile",
                    "Marketing Plan",
                ],
                "Financial Management & Compliance": [
                    "Business Operations Plan",
                    "Funding Linkages",
                ],
            },
            "Chedza Young Professional": {
                "Marketing & Sales": [
                    "Business Cards",
                    "Social Media Page Setup",
                ],
                "Technology & Digital Support": [
                    "Industry Training (Courses)",
                    "Excel Skills Training",
                ],
            },
            "Difokeng Africa": {
                "Marketing & Sales": [
                    "Business Cards",
                    "Company Profile",
                ],
                "Business & Financial Management": [
                    "Regulatory Compliance",
                    "Financial Literacy Mentoring",
                ],
            },
            "Food of Joy": {
                "Marketing & Sales": [
                    "Branded Banner",
                    "Social Media Page Setup",
                ],
                "Technology & Digital Support": [
                    "Technology Application Support",
                    "Project Facilitation",
                ],
            },
            "Frandmolf Enterprise": {
                "Marketing & Sales": [
                    "Pamphlets & Brochures",
                    "Industry Membership",
                ],
                "Financial Management & Compliance": [
                    "Management Accounts",
                    "Funding Linkages",
                ],
            },
            "Jaagbaan Lodge Capital": {
                "Marketing & Sales": [
                    "Company Profile",
                    "Marketing Linkages Time",
                ],
                "Technology & Digital Support": [
                    "Data Support",
                    "Excel Skills Training",
                ],
            },
            "Keitsile General Trading": {
                "Marketing & Sales": [
                    "Website Development & Domain Email Reg",
                    "Pamphlets & Brochures",
                ],
                "Financial Management & Compliance": [
                    "Insurance Tips Webinar",
                    "Regulatory Compliance",
                ],
            },
            "Kele Pheko Trading Lodge": {
                "Marketing & Sales": [
                    "Social Media Page Setup",
                    "Branded Banner",
                ],
                "Financial Management & Compliance": [
                    "Risk Management Plan",
                    "Business Operations Plan",
                ],
            },
            "Lapizi Trading": {
                "Marketing & Sales": [
                    "Industry Membership",
                    "Company Profile",
                ],
                "Technology & Digital Support": [
                    "Digital Transformation",
                    "Industry Seminars",
                ],
            },
            "Lesoslo Lodge": {
                "Marketing & Sales": [
                    "Pamphlets & Brochures",
                    "Marketing Linkages Time",
                ],
                "Technology & Digital Support": [
                    "Technology Application Support",
                    "Growth Plan",
                ],
            },
        }

        # ==================== Ensure Session State Exists ====================
        if "selected_enterprise" not in st.session_state:
            st.session_state.selected_enterprise = list(enterprise_hub_map.keys())[0]
        if "selected_hub" not in st.session_state:
            st.session_state.selected_hub = enterprise_hub_map[st.session_state.selected_enterprise]
        if "selected_province" not in st.session_state:
            st.session_state.selected_province = hub_province_map[st.session_state.selected_hub]
        if "selected_area_of_support" not in st.session_state:
            st.session_state.selected_area_of_support = list(enterprise_data[st.session_state.selected_enterprise].keys())[0]
        if "selected_intervention" not in st.session_state:
            st.session_state.selected_intervention = enterprise_data[st.session_state.selected_enterprise][st.session_state.selected_area_of_support][0]

        # ==================== Callbacks for Dynamic Updates ====================
        def update_hub_and_province():
            st.session_state.selected_hub = enterprise_hub_map[st.session_state.selected_enterprise]
            st.session_state.selected_province = hub_province_map[st.session_state.selected_hub]
            st.session_state.selected_area_of_support = list(enterprise_data[st.session_state.selected_enterprise].keys())[0]
            st.session_state.selected_intervention = enterprise_data[st.session_state.selected_enterprise][st.session_state.selected_area_of_support][0]

        def update_intervention():
            st.session_state.selected_intervention = enterprise_data[st.session_state.selected_enterprise][st.session_state.selected_area_of_support][0]

        # ==================== Selections (OUTSIDE THE FORM) ====================
        st.subheader("📋 Add New Intervention Entry")

        enterprise = st.selectbox("🏢 Enterprise", list(enterprise_hub_map.keys()),
                                  key="selected_enterprise",
                                  on_change=update_hub_and_province)

        # Show dynamic hub & province (Disabled Inputs)
        st.text_input("📍 Hub", st.session_state.selected_hub, disabled=True)
        st.text_input("🌍 Province", st.session_state.selected_province, disabled=True)

        # Area of Support Selection
        areas_of_support = list(enterprise_data[st.session_state.selected_enterprise].keys())
        selected_area_of_support = st.selectbox("📖 Select Area of Support", areas_of_support,
                                                key="selected_area_of_support",
                                                on_change=update_intervention)

        # Intervention Selection
        interventions = enterprise_data[st.session_state.selected_enterprise][st.session_state.selected_area_of_support]
        selected_intervention = st.selectbox("🛠️ Select Intervention", interventions,
                                             key="selected_intervention")

        # ==================== Form (WITH SUBMIT BUTTON) ====================
        with st.form("intervention_form"):
            poe = st.text_input("📄 POE Number")
            consultant1 = st.text_input("👨‍💼 Consultant 1")
            consultant2 = st.text_input("👩‍💼 Consultant 2")
            consultant3 = st.text_input("👩‍💼 Consultant 3")
            comment = st.text_area("📝 Comments")

            # Auto-fill Date & Quarter
            today = datetime.today()
            date_str = today.strftime("%d-%b-%y")
            month_str = today.strftime("%B")
            quarter_map = {
                1: "Q4", 2: "Q4", 3: "Q4",  # January - March (Q4)
                4: "Q1", 5: "Q1", 6: "Q1",  # April - June (Q1)
                7: "Q2", 8: "Q2", 9: "Q2",  # July - September (Q2)
                10: "Q3", 11: "Q3", 12: "Q3"  # October - December (Q3)
            }
            quarter_str = quarter_map[today.month]

            st.write(f"📅 Date: {date_str}, 📆 Month: {month_str}, 🔢 Quarter: {quarter_str}")

            submit_button = st.form_submit_button("✅ Submit Entry")

        # ==================== Process Submission ====================
        if submit_button:
            intervention_key = f"Number of SMMEs {st.session_state.selected_intervention}"
            actual_col = f"{st.session_state.selected_hub} {quarter_str} Actual"

            if actual_col in structured_df.columns:
                structured_df.loc[
                    (structured_df["Output"] == st.session_state.selected_area_of_support) &
                    (structured_df["Intervention"] == intervention_key),
                    actual_col
                ] += 1

            with open(DATA_FILE, "wb") as file:
                pickle.dump(structured_df, file)

            new_entry = pd.DataFrame([{
                "Enterprise": st.session_state.selected_enterprise,
                "Province": st.session_state.selected_province,
                "Hub": st.session_state.selected_hub,
                "Date": date_str,
                "Month": month_str,
                "Quarter": quarter_str,
                "Area of Support": st.session_state.selected_area_of_support,
                "Intervention": st.session_state.selected_intervention,
                "POE": poe,
                "Consultant 1": consultant1,
                "Consultant 2": consultant2,
                "Consultant 3": consultant3,
                "Comments": comment
            }])

            actuals_df = pd.concat([actuals_df, new_entry], ignore_index=True)
            with open(ACTUALS_FILE, "wb") as file:
                pickle.dump(actuals_df, file)

            st.success("✅ Entry successfully saved!")

        st.write("### 📋 Captured Intervention Entries")
        st.dataframe(actuals_df, use_container_width=True)
# ================== NON-ADMIN VIEW ==================
elif st.session_state.role == "user":
    st.title("📅 Data Entry for Revenue & Temporary Workers")

    # User selects Year
    year = st.selectbox("📆 Select Year", ["2024", "2025"])

    # User selects Month
    month = st.selectbox(
        "📅 Select Month",
        ["January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"]
    )

    # User inputs Revenue
    revenue = st.number_input("💰 Enter Revenue (ZAR)")

    # User inputs Temporary Workers
    temp_workers = st.number_input("👷 Number of Temporary Workers", min_value=1, step=1)

    # Submit Button
    if st.button("✅ Submit Entry"):
        # Save data to a local CSV file (or database if needed)
        entry_data = pd.DataFrame([{
            "Year": year,
            "Month": month,
            "Revenue": revenue,
            "Temporary Workers": temp_workers
        }])

        DATA_ENTRY_FILE = "user_data_entries.csv"

        if os.path.exists(DATA_ENTRY_FILE):
            existing_data = pd.read_csv(DATA_ENTRY_FILE)
            updated_data = pd.concat([existing_data, entry_data], ignore_index=True)
        else:
            updated_data = entry_data

        updated_data.to_csv(DATA_ENTRY_FILE, index=False)

        st.success("✅ Data successfully saved!")
        st.dataframe(updated_data)

    # Display previously saved data
    if os.path.exists("user_data_entries.csv"):
        st.write("### 📋 Previous Entries")
        saved_data = pd.read_csv("user_data_entries.csv")
        st.dataframe(saved_data, use_container_width=True)

    # Logout Button
    st.button("🚪 Logout", on_click=logout)
