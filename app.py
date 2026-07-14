import streamlit as st
import pandas as pd

# Set up the page layout
st.set_page_config(page_title="Bib Number Database", layout="wide")
st.title("🏃‍♂️ Bib Number Search & Status Tracker")
st.write("Upload your Excel sheet to search participants and update their status.")

# 1. Excel File Uploader
uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])

if uploaded_file is not None:
    # Load data into a session state so updates persist during the user session
    if "df" not in st.session_state:
        try:
            df = pd.read_excel(uploaded_file)
            
            # Ensure the required columns exist
            required_cols = ["Name", "Phone Number", "Email", "Bib Number", "Status"]
            for col in required_cols:
                if col not in df.columns:
                    # Create the column if it's missing (e.g., Status might be empty initially)
                    if col == "Status":
                        df["Status"] = False
                    else:
                        df[col] = ""
            
            # Clean up the Status column to make sure it's strictly boolean (True/False)
            df["Status"] = df["Status"].fillna(False).astype(bool)
            # Ensure Bib Number is treated as text or clean integers for easy searching
            df["Bib Number"] = df["Bib Number"].astype(str).str.replace(r'\.0$', '', regex=True)
            
            st.session_state.df = df
        except Exception as e:
            st.error(f"Error reading Excel file: {e}")
            st.stop()

    # Reference the session state dataframe
    working_df = st.session_state.df

    # 2. Search & Filter System
    st.subheader("🔍 Search Participants")
    search_query = st.text_input("Search by Name or Bib Number").strip().lower()

    # Filter data based on search input
    if search_query:
        filtered_df = working_df[
            working_df["Name"].astype(str).str.lower().str.contains(search_query) |
            working_df["Bib Number"].astype(str).str.lower().str.contains(search_query)
        ]
    else:
        filtered_df = working_df

    st.write(f"Showing {len(filtered_df)} of {len(working_df)} participants.")

    # 3. Interactive Data Editor (Handles Search, Display, and Checkboxes seamlessly)
    # st.data_editor turns the dataframe into a fully interactive UI grid
    edited_df = st.data_editor(
        filtered_df,
        column_config={
            "Status": st.column_config.CheckboxColumn(
                "Status (Checked In)",
                help="Tick to update status",
                default=False,
            ),
            "Phone Number": st.column_config.TextColumn("Phone Number"),
            "Bib Number": st.column_config.TextColumn("Bib Number"),
        },
        disabled=["Name", "Phone Number", "Email", "Bib Number"], # Only allow editing the Status checkbox
        use_container_width=True,
        key="data_editor_widget"
    )

    # 4. Save Changes back to Session State
    # Because st.data_editor returns the edited rows, we sync it back to our master dataframe
    if st.session_state.get("data_editor_widget"):
        edits = st.session_state["data_editor_widget"]["edited_rows"]
        for row_index, changes in edits.items():
            if "Status" in changes:
                # Find the actual index in the master dataframe matching the filtered row
                actual_idx = filtered_df.index[row_index]
                working_df.at[actual_idx, "Status"] = changes["Status"]

    # 5. Export / Download Updated Excel File
    st.markdown("---")
    st.subheader("💾 Export Data")
    
    # Convert updated dataframe to Excel bytes
    import io
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        working_df.to_excel(writer, index=False, sheet_name='Updated Status')
    
    st.download_button(
        label="Download Updated Excel Sheet",
        data=buffer.getvalue(),
        file_name="updated_bib_list.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("💡 Please upload an Excel file to get started. Make sure your file has headers matching: 'Name', 'Phone Number', 'Email', 'Bib Number', and 'Status'.")
