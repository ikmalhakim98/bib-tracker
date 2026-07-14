import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Live Bib Database", layout="wide")
st.title("🏃‍♂️ Live Bib Search & Status Tracker")

# 1. Establish connection to your Google Sheet
# Streamlit handles the authentication safely behind the scenes
conn = st.connection("gsheets", type=GSheetsConnection)

# Read the current data live from the cloud spreadsheet
df = conn.read(ttl=0) # ttl=0 ensures it pulls live updates without caching data

# 2. Search Engine
search_query = st.text_input("Search by Name or Bib Number").strip().lower()

if search_query:
    filtered_df = df[
        df["Name"].astype(str).str.lower().str.contains(search_query) |
        df["Bib Number"].astype(str).str.lower().str.contains(search_query)
    ]
else:
    filtered_df = df

# 3. Interactive Data Grid
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

# 4. Save Edits Permanently to Google Sheets
# The moment a checkbox is clicked, this block rewrites the row straight to the cloud
if st.session_state.get("live_editor"):
    edits = st.session_state["live_editor"]["edited_rows"]
    if edits:
        for row_index, changes in edits.items():
            if "Status" in changes:
                actual_idx = filtered_df.index[row_index]
                df.at[actual_idx, "Status"] = changes["Status"]
        
        # This sends the updated dataframe right back to your live Google Sheet
        conn.update(data=df)
        st.success("Database synchronized successfully!")
