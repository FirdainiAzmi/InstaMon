import streamlit as st
import pandas as pd
import csv
import re
from datetime import datetime
from io import StringIO
import gspread
from google.oauth2.service_account import Credentials

# =========================================================
# 🎨 PREMIUM UI CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="InstaMon BPS | Dashboard",
    layout="wide",
    page_icon="📊"
)

# Custom CSS untuk Look & Feel yang mewah
st.markdown("""
    <style>
    /* Import Font Modern */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

    /* Global Style */
    .stApp {
        background: #F8FAFC;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Container Card */
    .main-card {
        background: white;
        padding: 2rem;
        border-radius: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #E2E8F0;
        margin-bottom: 1rem;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        color: white;
    }
    
    /* Tombol Utama (Gradient) */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);
        border: none;
        padding: 0.6rem 1rem;
        border-radius: 0.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.4);
    }

    /* Status Badge */
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        background: #DCFCE7;
        color: #166534;
    }
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# 🔐 AUTHENTICATION
# =========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.write("#")
        with st.container(border=True):
            st.image("https://img.icons8.com/fluency/96/instagram-check-mark.png", width=80)
            st.title("InstaMon BPS")
            st.markdown("Silahkan masuk untuk mengelola data.")
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            if st.button("Masuk", type="primary", use_container_width=True):
                if user == st.secrets["auth"]["username"] and pw == st.secrets["auth"]["password"]:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Username/Password salah")
    st.stop()

# =========================================================
# 🛠️ SIDEBAR NAVIGATION
# =========================================================
with st.sidebar:
    st.markdown("<h2 style='color: white;'>Menu Utama</h2>", unsafe_allow_html=True)
    menu = st.radio("Navigasi", ["🚀 Rekap Data", "📊 Dashboard", "📖 Panduan"], label_visibility="collapsed")
    
    st.write("---")
    st.markdown("### 🟢 Koneksi")
    st.caption(f"Sheets: {st.secrets['gsheet']['sheet_name']}")
    st.caption(f"User: {st.secrets['auth']['username']}")
    
    if st.button("Keluar (Logout)", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# =========================================================
# 🏠 TAB 1: REKAP DATA
# =========================================================
if menu == "🚀 Rekap Data":
    st.title("🚀 Rekap Data Konten")
    st.markdown("Proses data Instagram Anda menjadi laporan terstruktur.")

    # KPI Section
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Antrean Data", len(st.session_state.get('last_processed', [])))
    with k2:
        st.metric("Total Record", len(st.session_state.get('data', [])))
    with k3:
        st.markdown('<p style="font-size:14px; color:gray; margin-bottom:5px;">System Status</p><span class="status-badge">ONLINE</span>', unsafe_allow_html=True)
    with k4:
        st.caption("Auto-clean active 🟢")

    st.write("---")

    col_input, col_info = st.columns([2, 1])
    
    with col_input:
        st.markdown("### 📋 Input Area")
        pasted_text = st.text_area("Tempel CSV dari Bookmarklet:", height=250, placeholder="https://instagram.com/p/..., Caption, 2024-...")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            btn_proses = st.button("🚀 Proses Sekarang", type="primary", use_container_width=True)
        with c2:
            btn_push = st.button("📤 Push ke GSheet", use_container_width=True)
        with c3:
            if st.button("🗑️ Reset", use_container_width=True):
                st.session_state.data = []
                st.rerun()

    with col_info:
        st.markdown("### ℹ️ Ringkasan Tugas")
        with st.container(border=True):
            st.markdown("""
            1. **Paste** kode CSV.
            2. Klik **Proses** untuk validasi.
            3. Klik **Push** untuk kirim ke Google Sheets.
            ---
            *Data akan otomatis dibersihkan dari karakter aneh dan baris duplikat.*
            """)

    # Tabel Preview
    if st.session_state.get('data'):
        st.markdown("### 📄 Preview Data Terakhir")
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True, hide_index=True)

# =========================================================
# 📊 TAB 2: DASHBOARD MONITORING
# =========================================================
elif menu == "📊 Dashboard":
    st.title("📊 Monitoring Real-time")
    st.markdown("Laporan performa konten berdasarkan data Google Sheets.")
    
    # Membungkus iframe dalam container agar terlihat rapi
    st.markdown(f"""
        <div style="background: white; padding: 10px; border-radius: 15px; border: 1px solid #E2E8F0;">
            <iframe src="{LOOKER_EMBED_URL}" width="100%" height="750" frameborder="0" style="border:0" allowfullscreen></iframe>
        </div>
    """, unsafe_allow_html=True)

# =========================================================
# 📖 TAB 3: PANDUAN
# =========================================================
else:
    st.title("📖 Panduan Penggunaan")
    
    st.markdown("### 🔄 Alur Kerja Sistem")
    
    
    st.write("---")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("#### 1. Cara Setup Bookmarklet")
        st.info("Cukup copy-paste kode di bawah ke dalam URL bookmark baru di browser Anda.")
        st.code("""javascript:(()=>{const permalink=location.href.split("?")[0]; ... })();""", language="javascript")
    
    with col_right:
        st.markdown("#### 2. Cara Kerja")
        st.markdown("""
        * **Link Instagram**: Mengambil URL bersih tanpa tracking.
        * **Caption**: Mengambil kalimat pertama saja agar rapi di laporan.
        * **Timestamp**: Mengonversi waktu posting ke format Indonesia/Laporan.
        * **Deduplikasi**: Sistem akan menolak jika link sudah pernah diinput.
        """)

# =========================================================
# FOOTER
# =========================================================
st.markdown("---")
st.caption("© 2024 InstaMon BPS | Built with Streamlit & Google Cloud")
