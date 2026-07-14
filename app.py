import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Live Bib Database", layout="wide")
st.title("🏃‍♂️ Live Bib Search & Status Tracker")

# File path inside your repository
DATA_FILE = "participants.csv"

# Load the data from the repository file
if os.path.exists(DATA_FILE):
    # We load it into session state so it handles quick updates efficiently
    if "df" not in st.session_state:
        st.session_state.df = pd.read_csv(DATA_FILE)
else:
    st.error("Missing 'participants.csv' file in your directory!")
    st.stop()

df = st.session_state.df

# Ensure columns are typed properly
df["Status"] = df["Status"].fillna(False).astype(bool)
df["Bib Number"] = df["Bib Number"].astype(str)

# 1. Search Bar
search_query = st.text_input("Search by Name or Bib Number").strip().lower()

if search_query:
    filtered_df = df[
        df["Name"].astype(str).str.lower().str.contains(search_query) |
        df["Bib Number"].astype(str).str.lower().str.contains(search_query)
    ]
else:
    filtered_df = df

# 2. Interactive Data Grid
edited_df = st.data_editor(
    filtered_df,
    column_config={
        "Status": st.column_config.CheckboxColumn("Status (Checked In)", default=False),
        "Bib Number": st.column_config.TextColumn("Bib Number"),
    },
    disabled=["Name", "Phone Number", "Email", "Bib Number"],
    use_container_width=True,
    key="live_editor"
)

# 3. Save Changes Instantly to the File
if st.session_state.get("live_editor"):
    edits = st.session_state["live_editor"]["edited_rows"]
    if edits:
        for row_index, changes in edits.items():
            if "Status" in changes:
                actual_idx = filtered_df.index[row_index]
                df.at[actual_idx, "Status"] = changes["Status"]
        
        # Save back to the file locally on the cloud server
        df.to_csv(DATA_FILE, index=False)
        st.success("Changes saved successfully!")
