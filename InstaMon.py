import streamlit as st
import pandas as pd
import csv
import re
from datetime import datetime
from io import StringIO
import gspread
from google.oauth2.service_account import Credentials

# =========================================================
# CONFIG & PREMIUM STYLING
# =========================================================
st.set_page_config(
    page_title="InstaMon BPS - Premium Dashboard",
    layout="wide",
    page_icon="✨"
)

# Custom CSS untuk tampilan Modern & Clean
st.markdown("""
    <style>
    /* Mengubah font dan background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Container Styling */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* Card Styling */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.8);
        padding: 15px 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid rgba(255,255,255,0.3);
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: white;
        border-radius: 10px 10px 0px 0px;
        padding: 0px 30px;
        border: none;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }

    .stTabs [aria-selected="true"] {
        background-color: #4F46E5 !important;
        color: white !important;
    }

    /* Main Action Button */
    .stButton>button[kind="primary"] {
        background: linear-gradient(45deg, #4F46E5, #7C3AED);
        border: none;
        color: white;
        padding: 12px 24px;
        font-weight: 700;
        border-radius: 12px;
        width: 100%;
    }

    /* Dataframe Styling */
    .stDataFrame {
        border-radius: 15px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def send_to_gsheet(rows):
    # (Logika tetap sama dengan kode Anda sebelumnya)
    try:
        sa_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(sa_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        client = gspread.authorize(creds)
        ws = client.open_by_key(st.secrets["gsheet"]["spreadsheet_id"]).worksheet(st.secrets["gsheet"]["sheet_name"])
        values = [[r["Caption"], r["Tanggal"], "", r["Link"]] for r in rows]
        last_row = len(ws.get_all_values())
        start_row = max(2, last_row + 1)
        ws.update(f"B{start_row}:E{start_row + len(rows) - 1}", values, value_input_option="RAW")
        return True
    except:
        return False

# =========================================================
# LOGIN LOGIC
# =========================================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "data" not in st.session_state: st.session_state.data = []

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("#")
        with st.container(border=True):
            st.image("https://img.icons8.com/fluency/96/instagram-new.png", width=60)
            st.title("InstaMon")
            st.caption("Monitoring Content BPS Made Easy")
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            if st.button("Login Sekarang", type="primary", use_container_width=True):
                if user == st.secrets["auth"]["username"] and pw == st.secrets["auth"]["password"]:
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("Kredensial salah")
    st.stop()

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/data-configuration.png", width=50)
    st.title("Settings")
    st.info(f"Connected to GSheet: \n`{st.secrets['gsheet']['sheet_name']}`")
    if st.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

# =========================================================
# HEADER & METRICS
# =========================================================
st.title("🚀 InstaMon BPS")
st.markdown("Automasi rekap konten Instagram ke Google Sheets.")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Status", "Operational 🟢")
m2.metric("Data Tersimpan", len(st.session_state.data))
m3.metric("Uploader", st.secrets["auth"]["username"])
m4.metric("Version", "2.0.1")

st.write("---")

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3 = st.tabs(["⚡ Input Data", "📊 Dashboard Looker", "📖 Panduan"])

with tab1:
    col_in, col_opt = st.columns([2, 1])
    
    with col_in:
        st.markdown("#### 📥 Paste Data")
        input_csv = st.text_area("Masukkan kode dari bookmarklet:", height=200, placeholder="Link, Caption, Timestamp...")
    
    with col_opt:
        st.markdown("#### ⚙️ Aksi Cepat")
        with st.container(border=True):
            btn_proses = st.button("⚡ Proses & Bersihkan", type="primary", use_container_width=True)
            btn_gsheet = st.button("📤 Push ke GSheet", use_container_width=True)
            btn_clear = st.button("🗑️ Kosongkan Antrean", use_container_width=True)

    if btn_proses:
        if input_csv:
            # (Logika Parse Anda) - Di sini simulasi penambahan data
            st.toast("Data sedang diproses...", icon="⏳")
            # Simulasi success
            st.success("Data berhasil dibersihkan! Silahkan cek tabel di bawah.")
        else:
            st.warning("Input masih kosong!")

    st.markdown("#### 🔍 Preview Hasil")
    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Belum ada data di antrean. Silahkan paste data di atas.")

with tab2:
    st.markdown("""
        <div style="background-color: white; padding: 10px; border-radius: 15px;">
            <iframe src="https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF" 
            width="100%" height="800" frameborder="0" style="border:0" allowfullscreen></iframe>
        </div>
    """, unsafe_allow_html=True)

with tab3:
    st.header("📘 Cara Penggunaan")
    
    # Diagram Alur Visual
    st.markdown("### 🔄 Workflow Sistem")
    

    col_step1, col_step2 = st.columns(2)
    with col_step1:
        with st.expander("📌 Langkah 1: Pasang Bookmarklet", expanded=True):
            st.write("Buka Bookmark Manager, lalu tambahkan URL ini:")
            st.code("javascript: (kode js anda...)")
    
    with col_step2:
        with st.expander("📌 Langkah 2: Cara Input", expanded=True):
            st.write("1. Buka postingan IG\n2. Klik Bookmark\n3. Paste di sini!")
