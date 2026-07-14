import streamlit as st
import pandas as pd

st.set_page_config(page_title="Live Google Sheet Database", layout="wide")
st.title("🏃‍♂️ Live Bib Search & Status Tracker")

# 1. Input your public Google Sheet URL here
# Swap 'edit?usp=sharing' at the end of the link out with 'export?format=csv' so pandas can read/write it directly
SHEET_URL = "https://docs.google.com/spreadsheets/d/1JRa7royoM_rVcSaTdw0FmamQRsn1pN9MNsTX-eS2qoU/edit?usp=sharing"
CSV_URL = SHEET_URL.split("/edit")[0] + "/export?format=csv"

# Load data live from Google Sheets
if "df" not in st.session_state:
    try:
        st.session_state.df = pd.read_csv(CSV_URL)
    except Exception as e:
        st.error("Could not load Google Sheet. Please check the URL and sharing settings.")
        st.stop()

df = st.session_state.df

# Clean formatting
df["Status"] = df["Status"].fillna(False).astype(bool)
df["Bib Number"] = df["Bib Number"].astype(str).str.replace(r'\.0$', '', regex=True)

# 2. Search Bar Engine
search_query = st.text_input("Search by Name or Bib Number").strip().lower()

if search_query:
    filtered_df = df[
        df["Name"].astype(str).str.lower().str.contains(search_query) |
        df["Bib Number"].astype(str).str.lower().str.contains(search_query)
    ]
else:
    filtered_df = df

# 3. Interactive Checklist Table
edited_df = st.data_editor(
    filtered_df,
    column_config={
        "Status": st.column_config.CheckboxColumn("Status (Checked In)", default=False),
        "Bib Number": st.column_config.TextColumn("Bib Number"),
    },
    disabled=["Name", "Phone Number", "Email", "Bib Number"],
    use_container_width=True,
    key="sheet_editor"
)

# 4. Handle Edits
if st.session_state.get("sheet_editor"):
    edits = st.session_state["sheet_editor"]["edited_rows"]
    if edits:
        for row_index, changes in edits.items():
            if "Status" in changes:
                actual_idx = filtered_df.index[row_index]
                df.at[actual_idx, "Status"] = changes["Status"]
        
        st.success("Changes saved locally! Click below to send updates to Google Sheets.")

# 5. Push changes to Google Sheets
# Because we are bypassing complex API keys, we add a manual push button 
# that generates a convenient download link or lets you sync
st.markdown("---")
if st.button("🔄 Sync Changes Back to Google Sheet"):
    # Convert data back to CSV string
    csv_data = df.to_csv(index=False)
    st.info("To apply updates directly to your live Google Sheet without setup, you can either:")
    
    # Simple direct copy-paste backup method
    st.text_area("1. Copy this entire updated data block and paste it back over cell A1 in Google Sheets:", csv_data, height=150)
    
    # Direct export backup
    st.download_button(
        label="2. Download Updated CSV to import back into your Sheet",
        data=csv_data,
        file_name="synced_participants.csv",
        mime="text/csv"
    )
