import os
import urllib.parse
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Live Google Sheet Database", layout="wide")
st.title("🏃‍♂️ Live Bib Search & Status Tracker")

# 1. Google Sheet Configuration
SHEET_ID = "1rvpMk2eljyUmcoW1qFh7yk4kY8AWKrygabGCe67bzxU"
TAB_NAME = "Form responses 1"

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={TAB_NAME.replace(' ', '%20')}"
CACHE_FILE = "checked_in_cache.csv"

# Function to wipe cache
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

    # Remove Timestamp column if present
    df_loaded = df_loaded.drop(columns=["Timestamp"], errors="ignore")

    # Column mapping
    col_mapping = {}
    for col in df_loaded.columns:
        low = col.lower()
        if "name" in low or "nama" in low:
            col_mapping[col] = "Name"
        elif "bib" in low:
            col_mapping[col] = "Bib Number"

    if col_mapping:
        df_loaded = df_loaded.rename(columns=col_mapping)

    # Ensure 'Status' & 'WhatsApp Sent' columns exist
    if "Status" not in df_loaded.columns:
        df_loaded["Status"] = False
    if "WhatsApp Sent" not in df_loaded.columns:
        df_loaded["WhatsApp Sent"] = False

    df_loaded["Status"] = df_loaded["Status"].fillna(False).astype(bool)
    df_loaded["WhatsApp Sent"] = df_loaded["WhatsApp Sent"].fillna(False).astype(bool)

    if "Bib Number" in df_loaded.columns:
        df_loaded["Bib Number"] = df_loaded["Bib Number"].astype(str).str.replace(r'\.0$', '', regex=True)

    st.session_state.df = df_loaded

df = st.session_state.df

# 3. Search & Filter Controls (Multiselect Category)
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    search_query = st.text_input("Search by Name or Bib Number").strip()

with col2:
    if "Category" in df.columns:
        valid_cats = df["Category"].dropna().astype(str).str.strip()
        unique_cats = sorted([c for c in valid_cats.unique() if c and c.lower() not in ["none", "nan"]])
    else:
        unique_cats = []

    selected_categories = st.multiselect(
        "Filter by Category",
        options=unique_cats,
        placeholder="All Categories"
    )

with col3:
    status_filter = st.selectbox(
        "Filter by Status",
        options=["All", "Checked In (Ticked)", "Not Checked In (Unticked)"]
    )

# 4. Filter Logic
filtered_df = df.copy()

# Filter Search Query
if search_query:
    has_name = "Name" in filtered_df.columns
    has_bib = "Bib Number" in filtered_df.columns

    # Gunakan case=False dan na=False supaya carian case-insensitive & kebal error null
    name_mask = filtered_df["Name"].astype(str).str.contains(search_query, case=False, na=False) if has_name else False
    bib_mask = filtered_df["Bib Number"].astype(str).str.contains(search_query, case=False, na=False) if has_bib else False

    filtered_df = filtered_df[name_mask | bib_mask]

# Filter Category (Multiple Selection guna .isin)
if selected_categories and "Category" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["Category"].astype(str).str.strip().isin(selected_categories)]

# Filter Status
if status_filter == "Checked In (Ticked)":
    filtered_df = filtered_df[filtered_df["Status"] == True]
elif status_filter == "Not Checked In (Unticked)":
    filtered_df = filtered_df[filtered_df["Status"] == False]

disabled_cols = [col for col in filtered_df.columns if col not in ["Status", "WhatsApp Sent"]]

# 5. Interactive Table Editor
edited_df = st.data_editor(
    filtered_df,
    column_config={
        "Status": st.column_config.CheckboxColumn("Status (Checked In)", default=False),
        "WhatsApp Sent": st.column_config.CheckboxColumn("📲 WS Sent?", default=False),
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
            actual_idx = filtered_df.index[row_index]
            if "Status" in changes:
                st.session_state.df.at[actual_idx, "Status"] = changes["Status"]
            if "WhatsApp Sent" in changes:
                st.session_state.df.at[actual_idx, "WhatsApp Sent"] = changes["WhatsApp Sent"]

        st.session_state.df.to_csv(CACHE_FILE, index=False)
        st.rerun()

# 7. SECTION CUSTOM WHATSAPP MESSAGE (Only Pending Messages Shown)
st.markdown("---")
st.subheader("📲 Send WhatsApp Confirmation")

# Ambil peserta yang Dah Checked In TAPIIII Belum Hantar WhatsApp
pending_ws = st.session_state.df[(st.session_state.df["Status"] == True) & (st.session_state.df["WhatsApp Sent"] == False)]

if pending_ws.empty:
    st.success("🎉 Semua peserta yang Checked In telah dihantar WhatsApp!")
else:
    selected_person_idx = st.selectbox(
        "Pilih Peserta yang Belum Dihantar WhatsApp:",
        options=pending_ws.index,
        format_func=lambda idx: f"⏳ {pending_ws.loc[idx, 'Name']} | Phone: {pending_ws.loc[idx, 'Phone Number'] if 'Phone Number' in pending_ws.columns else 'N/A'}"
    )

    if selected_person_idx is not None:
        row = pending_ws.loc[selected_person_idx]

        # Clean phone format
        raw_phone = str(row.get("Phone Number", "")).strip().replace(".0", "")
        clean_phone = raw_phone.replace("+", "").replace("-", "").replace(" ", "")
        if clean_phone.startswith("0"):
            clean_phone = "6" + clean_phone
        elif clean_phone.startswith("1") and not clean_phone.startswith("60"):
            clean_phone = "60" + clean_phone

        name = row.get("Name", "Runner")
        wristband = str(row.get("Order ID", "-")).replace(".0", "")
        category = str(row.get("Category", "-")).replace("nan", "-")

        # Custom WhatsApp Message
        custom_message = (
            f"Hi {name}! 👋\n\n"
            f"You have collected your medal! 🎉\n\n"
            f"Congratulations on your achievement!"
        )

        encoded_msg = urllib.parse.quote(custom_message)
        wa_url = f"https://wa.me/{clean_phone}?text={encoded_msg}"

        wa_col1, wa_col2 = st.columns([3, 1])

        with wa_col1:
            st.text_area("Preview Mesej WhatsApp:", custom_message, height=150)

        with wa_col2:
            st.write(" ")
            st.write(" ")
            if st.link_button("🚀 SEND TO WHATSAPP", wa_url, type="primary", use_container_width=True):
                pass

            if st.button("✅ Mark as WhatsApp Sent", use_container_width=True):
                st.session_state.df.at[selected_person_idx, "WhatsApp Sent"] = True
                st.session_state.df.to_csv(CACHE_FILE, index=False)
                st.toast(f"Marked WS Sent for {name}!")
                st.rerun()

# 8. Backup & Export
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
