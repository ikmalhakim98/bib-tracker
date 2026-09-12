import io
import os
import urllib.parse
import urllib.request
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Medal Engraving & Status Tracker", layout="wide")
st.title("🏃‍♂️ Medal Engraving & Status Tracker")

# 1. Google Sheet Configuration
SHEET_ID = "1rvpMk2eljyUmcoW1qFh7yk4kY8AWKrygabGCe67bzxU"
TAB_NAME = "Form responses 1"

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet={urllib.parse.quote(TAB_NAME)}"
FALLBACK_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(TAB_NAME)}"
CACHE_FILE = "checked_in_cache.csv"

# Function to wipe cache
def wipe_cache_and_reset():
    if os.path.exists(CACHE_FILE):
        try:
            os.remove(CACHE_FILE)
        except Exception as e:
            st.error(f"Error removing cache file: {e}")

    for key in list(st.session_state.keys()):
        del st.session_state[key]

# Sidebar Controls
st.sidebar.title("⚙️ Controls")
if st.sidebar.button("🚨 FORCE WIPE CACHE & LOAD FORM RESPONSES"):
    wipe_cache_and_reset()
    st.sidebar.success("Cache dipadam! Memuat turun data baru daripada Google Sheet...")
    st.rerun()

# Helper untuk tarik CSV dengan custom browser User-Agent & paksa baca sebagai string
def fetch_sheet_csv(primary_url, fallback_url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        req = urllib.request.Request(primary_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            return pd.read_csv(io.StringIO(response.read().decode("utf-8")), dtype=str)
    except Exception:
        req = urllib.request.Request(fallback_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            return pd.read_csv(io.StringIO(response.read().decode("utf-8")), dtype=str)

# 2. Load Data Logic
if "df" not in st.session_state:
    if os.path.exists(CACHE_FILE):
        df_loaded = pd.read_csv(CACHE_FILE, dtype=str)
    else:
        try:
            df_loaded = fetch_sheet_csv(CSV_URL, FALLBACK_URL)
        except Exception as e:
            st.error(f"❌ Gagal menyambung ke '{TAB_NAME}' di Google Sheet.")
            st.error(f"Maklumat Ralat: {e}")
            st.info("Pastikan Google Sheet diset: **General Access -> Anyone with the link -> Viewer**.")
            st.stop()

    # Bersihkan nama lajur & buang lajur kosong / Unnamed
    df_loaded.columns = df_loaded.columns.astype(str).str.strip()
    df_loaded = df_loaded.loc[:, ~df_loaded.columns.str.startswith("Unnamed")]
    df_loaded = df_loaded.loc[:, df_loaded.columns != ""]

    # Buang lajur Timestamp & sebarang lajur berkaitan Consent / Column 7
    cols_to_drop = [
        col for col in df_loaded.columns 
        if any(term in col.lower() for term in ["timestamp", "consent", "column 7", "confirm", "setuju"])
    ]
    df_loaded = df_loaded.drop(columns=cols_to_drop, errors="ignore")

    # Column mapping selamat (Auto-detect Name, Wristband/Bib, Phone)
    col_mapping = {}
    found_name = False
    found_wristband = False
    found_phone = False

    for col in df_loaded.columns:
        low = col.lower()
        if not found_name and ("name" in low or "nama" in low):
            col_mapping[col] = "Name"
            found_name = True
        elif not found_wristband and any(k in low for k in ["wristband", "wistband", "band", "order id", "bib"]):
            col_mapping[col] = "Wristband Number"
            found_wristband = True
        elif not found_phone and any(k in low for k in ["phone", "tel", "contact", "mobile", "whatsapp", "no tel"]):
            col_mapping[col] = "Phone Number"
            found_phone = True

    if col_mapping:
        df_loaded = df_loaded.rename(columns=col_mapping)

    # Buang duplicate column names jika masih wujud
    df_loaded = df_loaded.loc[:, ~df_loaded.columns.duplicated()]

    # Pastikan lajur 'Status' & 'WhatsApp Sent' wujud & convert kepada boolean
    if "Status" not in df_loaded.columns:
        df_loaded["Status"] = False
    if "WhatsApp Sent" not in df_loaded.columns:
        df_loaded["WhatsApp Sent"] = False

    df_loaded["Status"] = df_loaded["Status"].fillna(False).astype(str).str.lower().isin(["true", "1", "yes"])
    df_loaded["WhatsApp Sent"] = df_loaded["WhatsApp Sent"].fillna(False).astype(str).str.lower().isin(["true", "1", "yes"])

    # Bersihkan Wristband Number tanpa menambah angka 0 di depan
    if "Wristband Number" in df_loaded.columns:
        def clean_wristband(val):
            if pd.isna(val):
                return None
            s = str(val).strip().replace(".0", "")
            if s.lower() in ["none", "nan", ""]:
                return None
            return s

        df_loaded["Wristband Number"] = df_loaded["Wristband Number"].apply(clean_wristband)

    st.session_state.df = df_loaded

df = st.session_state.df

# 3. Search & Filter Controls
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    search_query = st.text_input("Search by Name, Wristband, or Phone Number").strip()

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
        options=["All", "Collected (Ticked)", "Not Collected (Unticked)"]
    )

# 4. Filter Logic (Menyokong Name, Wristband, dan Phone Number)
filtered_df = df.copy()

if search_query:
    has_name = "Name" in filtered_df.columns
    has_wristband = "Wristband Number" in filtered_df.columns
    has_phone = "Phone Number" in filtered_df.columns

    if has_name:
        name_clean = filtered_df["Name"].fillna("").astype(str).str.strip()
        name_clean = name_clean.replace(["None", "nan", "<NA>"], "")
        name_mask = name_clean.str.contains(search_query, case=False, na=False)
    else:
        name_mask = False

    if has_wristband:
        wrist_clean = filtered_df["Wristband Number"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        wrist_clean = wrist_clean.replace(["None", "nan", "<NA>"], "")
        wristband_mask = wrist_clean.str.contains(search_query, case=False, na=False)
    else:
        wristband_mask = False

    if has_phone:
        phone_clean = filtered_df["Phone Number"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        phone_clean = phone_clean.replace(["None", "nan", "<NA>"], "")
        phone_mask = phone_clean.str.contains(search_query, case=False, na=False)
    else:
        phone_mask = False

    filtered_df = filtered_df[name_mask | wristband_mask | phone_mask]

if selected_categories and "Category" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["Category"].astype(str).str.strip().isin(selected_categories)]

if status_filter == "Collected (Ticked)":
    filtered_df = filtered_df[filtered_df["Status"] == True]
elif status_filter == "Not Collected (Unticked)":
    filtered_df = filtered_df[filtered_df["Status"] == False]

disabled_cols = [col for col in filtered_df.columns if col not in ["Status", "WhatsApp Sent"]]

# 5. Interactive Table Editor
edited_df = st.data_editor(
    filtered_df,
    column_config={
        "Status": st.column_config.CheckboxColumn("Status (Collected)", default=False),
        "WhatsApp Sent": st.column_config.CheckboxColumn("📲 WS Sent?", default=False),
        "Wristband Number": st.column_config.TextColumn("Wristband Number"),
        "Phone Number": st.column_config.TextColumn("Phone Number"),
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

# 7. SECTION CUSTOM WHATSAPP MESSAGE
st.markdown("---")
st.subheader("📲 Send WhatsApp Confirmation")

pending_ws = st.session_state.df[(st.session_state.df["Status"] == True) & (st.session_state.df["WhatsApp Sent"] == False)]

if pending_ws.empty:
    st.success("🎉 Semua peserta yang Collected telah dihantar WhatsApp!")
else:
    def get_dropdown_label(idx):
        p_name = pending_ws.loc[idx, "Name"] if "Name" in pending_ws.columns else "Runner"
        if "Phone Number" in pending_ws.columns and pd.notna(pending_ws.loc[idx, "Phone Number"]):
            p_phone = str(pending_ws.loc[idx, "Phone Number"]).strip().replace(".0", "")
            if not p_phone or p_phone.lower() == "nan":
                p_phone = "N/A"
        else:
            p_phone = "N/A"
        return f"⏳ {p_name} | Phone: {p_phone}"

    selected_person_idx = st.selectbox(
        "Pilih Peserta yang Belum Dihantar WhatsApp:",
        options=pending_ws.index,
        format_func=get_dropdown_label
    )

    if selected_person_idx is not None:
        row = pending_ws.loc[selected_person_idx]

        raw_phone = ""
        if "Phone Number" in row and pd.notna(row["Phone Number"]):
            raw_phone = str(row["Phone Number"]).strip().replace(".0", "")

        clean_phone = "".join(filter(str.isdigit, raw_phone))
        if clean_phone.startswith("0"):
            clean_phone = "6" + clean_phone
        elif clean_phone.startswith("1") and not clean_phone.startswith("60"):
            clean_phone = "60" + clean_phone

        name = row.get("Name", "Runner")

        custom_message = (
            f"Hi {name}! \n\n"
            f"You have collected your medal! \n\n"
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
