import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Live Google Sheet Database", layout="wide")
st.title("🏃‍♂️ Live Bib Search & Status Tracker")

# 1. Google Sheet Configuration (Updated Sheet ID and Tab Name)
SHEET_ID = "1rvpMk2eljyUmcoW1qFh7yk4kY8AWKrygabGCe67bzxU"
TAB_NAME = "Form responses 1"

# Target 'Form responses 1' tab using GViz endpoint
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={TAB_NAME.replace(' ', '%20')}"
CACHE_FILE = "checked_in_cache.csv"

# Function to physically delete cache on disk and reset session memory
def wipe_cache_and_reset():
    if os.path.exists(CACHE_FILE):
        try:
            os.remove(CACHE_FILE)
        except Exception as e:
            st.error(f"Error removing file: {e}")
            
    for key in list(st.session_state.keys()):
        del st.session_state[key]

# Sidebar Controls
st.sidebar.title("⚙️ Controls")
if st.sidebar.button("🚨 FORCE WIPE CACHE & LOAD FORM RESPONSES"):
    wipe_cache_and_reset()
    st.sidebar.success("Cache deleted! Pulling fresh data from Google Sheet...")
    st.rerun()

# 2. Load Data Logic
if "df" not in st.session_state:
    if os.path.exists(CACHE_FILE):
        df_loaded = pd.read_csv(CACHE_FILE)
    else:
        try:
            df_loaded = pd.read_csv(CSV_URL)
        except Exception as e:
            st.error(f"❌ Could not load '{TAB_NAME}' from Google Sheet.")
            st.error("Please ensure General Access on the Google Sheet is set to 'Anyone with the link can view'.")
            st.stop()

    # Clean up column whitespaces
    df_loaded.columns = df_loaded.columns.astype(str).str.strip()

    # Flexible column mapping (Finds 'Name' / 'Nama' and 'Bib' columns automatically)
    col_mapping = {}
    for col in df_loaded.columns:
        low = col.lower()
        if "name" in low or "nama" in low:
            col_mapping[col] = "Name"
        elif "bib" in low:
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

# --- DEBUG INFO HEADER ---
with st.expander("🔍 Debug Info (Click to verify pulled columns)", expanded=True):
    st.write("**Using Source URL:**", CSV_URL)
    st.write("**Detected Columns:**", list(df.columns))
    st.write("**Total Rows Loaded:**", len(df))
    st.dataframe(df.head(5))

# 3. Search & Filter Controls
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input("Search by Name or Bib Number").strip().lower()

with col2:
    status_filter = st.selectbox(
        "Filter by Status",
        options=["All", "Checked In (Ticked)", "Not Checked In (Unticked)"]
    )

# 4. Filter Logic
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

disabled_cols = [col for col in filtered_df.columns if col != "Status"]

# 5. Interactive Table Editor
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

# 6. Handle Edits & Instantly Save Locally
if st.session_state.get("sheet_editor"):
    edits = st.session_state["sheet_editor"]["edited_rows"]
    if edits:
        for row_index, changes in edits.items():
            if "Status" in changes:
                actual_idx = filtered_df.index[row_index]
                st.session_state.df.at[actual_idx, "Status"] = changes["Status"]

        # Save to local file so ticks are preserved when you refresh
        st.session_state.df.to_csv(CACHE_FILE, index=False)

# 7. Backup & Export
st.markdown("---")
if st.button("💾 Export / Backup Data"):
    csv_data = st.session_state.df.to_csv(index=False)
    st.text_area("Copy updated data:", csv_data, height=150)
    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name="synced_participants.csv",
        mime="text/csv"
    )
