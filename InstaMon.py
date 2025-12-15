import streamlit as st
import pandas as pd
import csv
import re
import traceback
from datetime import datetime
from io import StringIO

import gspread
from google.oauth2.service_account import Credentials

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="InstaMon BPS",
    layout="wide",
    page_icon="📊"
)

LOOKER_EMBED_URL = "https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF"

# =========================================================
# SESSION STATE
# =========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "data" not in st.session_state:
    st.session_state.data = []

if "last_processed" not in st.session_state:
    st.session_state.last_processed = []

# =========================================================
# LOGIN PAGE
# =========================================================
def login_page():
    st.markdown("## 🔐 Login InstaMon BPS")

    with st.container(border=True):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", use_container_width=True):
            if (
                username == st.secrets["auth"]["username"]
                and password == st.secrets["auth"]["password"]
            ):
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("❌ Username atau password salah")

if not st.session_state.logged_in:
    login_page()
    st.stop()

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def first_sentence(text):
    if not text:
        return ""
    m = re.search(r"(.+?[.!?])", text)
    return m.group(1) if m else text

def clean_caption(text):
    text = (text or "").replace("\n", " ").replace("\r", " ")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = first_sentence(text)
    text = re.sub(r"[^A-Za-z0-9 ,.!?]+", " ", text)
    return " ".join(text.split()).strip()

def parse_csv_content(csv_text, existing_links):
    reader = csv.reader(StringIO(csv_text))
    hasil = []
    skipped = 0

    for row in reader:
        if len(row) < 3:
            continue

        link, caption, ts = row[0].strip(), row[1], row[2]

        if not link or link in existing_links:
            skipped += 1
            continue

        existing_links.add(link)

        ts = ts.strip()
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")

        tanggal = datetime.fromisoformat(ts).strftime("%m-%d-%Y")

        hasil.append({
            "Caption": clean_caption(caption),
            "Tanggal": tanggal,
            "Link": link
        })

    return hasil, skipped

# =========================================================
# GOOGLE SHEETS
# =========================================================
def send_to_gsheet(rows):
    sa_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)

    spreadsheet_id = st.secrets["gsheet"]["spreadsheet_id"]
    sheet_name = st.secrets["gsheet"]["sheet_name"]

    ws = client.open_by_key(spreadsheet_id).worksheet(sheet_name)

    if (ws.acell("B1").value or "") == "":
        ws.update("B1", [["Caption"]])
    if (ws.acell("C1").value or "") == "":
        ws.update("C1", [["Tanggal"]])
    if (ws.acell("E1").value or "") == "":
        ws.update("E1", [["Link"]])

    last_row = len(ws.get_all_values())
    start_row = max(2, last_row + 1)
    end_row = start_row + len(rows) - 1

    values = []
    for r in rows:
        values.append([
            r["Caption"],   # B
            r["Tanggal"],   # C
            "",             # D
            r["Link"]       # E
        ])

    ws.update(f"B{start_row}:E{end_row}", values, value_input_option="RAW")

# =========================================================
# UI TABS
# =========================================================
tab1, tab2, tab3 = st.tabs([
    "🛠️ Input Data",
    "📊 Dashboard Monitoring",
    "📘 Informasi Penggunaan"
])

# =======================
# TAB 1 - INPUT DATA
# =======================
with tab1:
    st.markdown("## 🛠️ Input & Proses Data Instagram")
    st.caption("Format CSV: **link, caption, timestamp**")

    with st.container(border=True):
        pasted_text = st.text_area(
            "📋 Paste Data CSV",
            height=220
        )

    with st.expander("🔐 Informasi Service Account"):
        st.markdown("Share Google Sheet ke email ini sebagai **Editor**:")
        st.code(st.secrets["gcp_service_account"]["client_email"])

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🚀 Proses Data", use_container_width=True):
            if not pasted_text.strip():
                st.warning("Paste data terlebih dahulu.")
            else:
                existing_links = {d["Link"] for d in st.session_state.data}
                data_baru, skipped = parse_csv_content(
                    pasted_text,
                    existing_links
                )

                st.session_state.data.extend(data_baru)
                st.session_state.last_processed = data_baru

                st.success(f"✅ {len(data_baru)} data diproses")
                if skipped > 0:
                    st.warning(f"⚠️ {skipped} data dilewati (duplikat link)")

    with col2:
        if st.button("🗑️ Reset Data", use_container_width=True):
            st.session_state.data = []
            st.session_state.last_processed = []
            st.success("Data berhasil direset")

    with col3:
        if st.button("📤 Kirim ke Google Sheets", use_container_width=True):
            rows = st.session_state.last_processed
            if not rows:
                st.warning("Belum ada data baru.")
            else:
                send_to_gsheet(rows)
                st.success(f"✅ {len(rows)} baris terkirim ke Google Sheets")

    st.divider()

    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True)

        st.download_button(
            "⬇️ Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            "hasil_monitoring_instagram.csv",
            "text/csv"
        )
    else:
        st.info("Belum ada data.")

# =======================
# TAB 2 - DASHBOARD
# =======================
with tab2:
    st.markdown("## 📊 Dashboard Monitoring Instagram")
    st.components.v1.iframe(
        src=LOOKER_EMBED_URL,
        width=1400,
        height=720,
        scrolling=True
    )

# =======================
# TAB 3 - INFORMASI PENGGUNAAN
# =======================
with tab3:
    st.markdown("## 📘 Informasi Penggunaan Web InstaMon")

    st.markdown("""
    **InstaMon** adalah aplikasi internal untuk monitoring konten Instagram
    yang digunakan secara **manual, aman, dan non-otomatis**.

    Aplikasi ini **TIDAK melakukan scraping otomatis**
    dan **TIDAK mengambil data langsung dari Instagram**.
    """)

    st.divider()

    st.markdown("### 🔄 Alur Kerja")

    st.markdown("""
    1. Pengguna login ke Instagram melalui browser  
    2. Membuka satu postingan Instagram  
    3. Menjalankan **bookmarklet IG to CSV**  
    4. Bookmarklet menghasilkan **1 baris CSV**  
    5. Data CSV dipaste ke InstaMon  
    6. Data diproses dan dimonitor melalui dashboard
    """)

    st.divider()

    st.markdown("### 🔖 Bookmarklet")

    st.markdown("""
    Bookmarklet dijalankan **manual di browser pengguna**
    untuk mengambil:
    - Link postingan
    - Caption (kalimat pertama)
    - Timestamp unggahan
    """)

    st.info("Bookmarklet dijalankan pada browser yang sudah login Instagram.")

    st.divider()

    st.markdown("### 📋 Format Data")

    st.code("""
link,caption,timestamp
"https://instagram.com/p/xxxx","Isi caption","2024-01-01T10:00:00Z"
    """)

    st.divider()

    st.success("""
    ✅ Tidak ada scraping otomatis  
    ✅ Data diperoleh manual oleh pengguna  
    ✅ Aman untuk penggunaan internal
    """)
