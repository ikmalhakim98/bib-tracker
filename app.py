import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Live Google Sheet Database", layout="wide")
st.title("🏃‍♂️ Live Bib Search & Status Tracker")

# 1. Google Sheet URL configured for 'Form responses 1'
SHEET_URL = "https://docs.google.com/spreadsheets/d/1JRa7royoM_rVcSaTdw0FmamQRsn1pN9MNsTX-eS2qoU/edit?usp=sharing"
TAB_NAME = "Form responses 1"

# Target 'Form responses 1' tab
CSV_URL = SHEET_URL.split("/edit")[0] + f"/export?format=csv&sheet={TAB_NAME.replace(' ', '%20')}"

# Local cache file name to retain ticks after refresh
CACHE_FILE = "checked_in_cache.csv"

# Sidebar controls
st.sidebar.title("⚙️ Controls")
if st.sidebar.button("🔄 Reset & Pull Fresh Sheet"):
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    if "df" in st.session_state:
        del st.session_state["df"]
    st.sidebar.success("Cache cleared! Re-fetching Google Sheet...")
    st.rerun()

# Load data
if "df" not in st.session_state:
    if os.path.exists(CACHE_FILE):
        df_loaded = pd.read_csv(CACHE_FILE)
    else:
        try:
            df_loaded = pd.read_csv(CSV_URL)
        except Exception as e:
            st.error(f"Could not load '{TAB_NAME}' from Google Sheet. Make sure the sheet sharing is set to 'Anyone with the link can view'.")
            st.stop()

    # Clean column names (strip leading/trailing whitespace)
    df_loaded.columns = df_loaded.columns.str.strip()

    # Automatically map common Form field variations to standard names
    col_mapping = {}
    for col in df_loaded.columns:
        low_col = col.lower()
        if "name" in low_col or "nama" in low_col:
            col_mapping[col] = "Name"
        elif "bib" in low_col:
            col_mapping[col] = "Bib Number"

    if col_mapping:
        df_loaded = df_loaded.rename(columns=col_mapping)

    # Ensure 'Status' column exists
    if "Status" not in df_loaded.columns:
        df_loaded["Status"] = False

    df_loaded["Status"] = df_loaded["Status"].fillna(False).astype(bool)

    if "Bib Number" in df_loaded.columns:
        df_loaded["Bib Number"] = df_loaded["Bib Number"].astype(str).str.replace(r'\.0$', '', regex=True)

    st.session_state.df = df_loaded

df = st.session_state.df

# 2. Search & Filter Controls
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input("Search by Name or Bib Number").strip().lower()

with col2:
    status_filter = st.selectbox(
        "Filter by Status",
        options=["All", "Checked In (Ticked)", "Not Checked In (Unticked)"]
    )

# 3. Apply Filters
filtered_df = df.copy()

if search_query:
    has_name = "Name" in filtered_df.columns
    has_bib = "Bib Number" in filtered_df.columns

    name_mask = filtered_df["Name"].astype(str).str.lower().str.contains(search_query) if has_name else False
    bib_mask = filtered_df["Bib Number"].astype(str).str.lower().str.contains(search_query) if has_bib else False

    filtered_df = filtered_df[name_mask | bib_mask]

if status_filter == "Checked In (Ticked)":
    filtered_df = filtered_df[filtered_df["Status"] == True]
elif status_filter == "Not Checked In (Unticked)":
    filtered_df = filtered_df[filtered_df["Status"] == False]

# Disable editing on all columns except 'Status'
disabled_cols = [col for col in filtered_df.columns if col != "Status"]

# 4. Interactive Checklist Table
edited_df = st.data_editor(
    filtered_df,
    column_config={
        "Status": st.column_config.CheckboxColumn("Status (Checked In)", default=False),
        "Bib Number": st.column_config.TextColumn("Bib Number"),
    },
    disabled=disabled_cols,
    use_container_width=True,
    key="sheet_editor"
)

# 5. Handle Edits & Save Locally
if st.session_state.get("sheet_editor"):
    edits = st.session_state["sheet_editor"]["edited_rows"]
    if edits:
        for row_index, changes in edits.items():
            if "Status" in changes:
                actual_idx = filtered_df.index[row_index]
                st.session_state.df.at[actual_idx, "Status"] = changes["Status"]

        st.session_state.df.to_csv(CACHE_FILE, index=False)

# 6. Push changes back options
st.markdown("---")
if st.button("💾 Sync / Export Updated Data"):
    csv_data = st.session_state.df.to_csv(index=False)
    st.info("To apply updates directly to your live Google Sheet, you can either:")

    st.text_area("1. Copy this entire updated data block and paste it back into Google Sheets:", csv_data, height=150)

    st.download_button(
        label="2. Download Updated CSV to import back into your Sheet",
        data=csv_data,
        file_name="synced_participants.csv",
        mime="text/csv"
    )
