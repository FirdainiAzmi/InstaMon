import streamlit as st
import pandas as pd
import csv
import re
from datetime import datetime
from io import StringIO
import gspread
from google.oauth2.service_account import Credentials

# =========================================================
# CONFIG & STYLING
# =========================================================
st.set_page_config(
    page_title="InstaMon BPS",
    layout="wide",
    page_icon="📊"
)

# Custom CSS untuk mempercantik UI
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        color: #007bff;
    }
    .status-card {
        padding: 20px;
        border-radius: 10px;
        background-color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

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
# LOGIN PAGE (Enhanced)
# =========================================================
def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("")
        st.write("")
        with st.container(border=True):
            st.image("https://img.icons8.com/fluency/96/data-configuration.png", width=80)
            st.title("InstaMon BPS")
            st.subheader("Silahkan Login")
            
            username = st.text_input("Username", placeholder="Masukkan username")
            password = st.text_input("Password", type="password", placeholder="Masukkan password")
            
            if st.button("Masuk Ke Sistem 🚀", use_container_width=True):
                if (username == st.secrets["auth"]["username"] 
                    and password == st.secrets["auth"]["password"]):
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
    if not text: return ""
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
        if len(row) < 3: continue
        link, caption, ts = row[0].strip(), row[1], row[2]
        if not link or link in existing_links:
            skipped += 1
            continue
        existing_links.add(link)
        ts = ts.strip().replace("Z", "+00:00") if ts.endswith("Z") else ts
        tanggal = datetime.fromisoformat(ts).strftime("%m-%d-%Y")
        hasil.append({"Caption": clean_caption(caption), "Tanggal": tanggal, "Link": link})
    return hasil, skipped

def send_to_gsheet(rows):
    sa_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(sa_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    ws = client.open_by_key(st.secrets["gsheet"]["spreadsheet_id"]).worksheet(st.secrets["gsheet"]["sheet_name"])
    
    last_row = len(ws.get_all_values())
    start_row = max(2, last_row + 1)
    values = [[r["Caption"], r["Tanggal"], "", r["Link"]] for r in rows]
    ws.update(f"B{start_row}:E{start_row + len(rows) - 1}", values, value_input_option="RAW")

# =========================================================
# MAIN UI
# =========================================================
st.sidebar.title("🛠️ Control Panel")
if st.sidebar.button("Logout", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

tab1, tab2, tab3 = st.tabs(["🚀 Rekap Data", "📊 Dashboard", "📘 Panduan"])

# =======================
# TAB 1 - REKAP DATA (Modernized)
# =======================
with tab1:
    # Row 1: Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Link Terdata", len(st.session_state.data))
    m2.metric("Data Baru Diproses", len(st.session_state.last_processed))
    m3.metric("Status Koneksi", "✅ GSheet Connected")

    st.divider()

    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.markdown("### 📋 Input Data")
        pasted_text = st.text_area(
            "Paste CSV dari bookmarklet di sini:",
            height=250,
            placeholder="link, caption, timestamp..."
        )
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🚀 Proses Data", use_container_width=True, type="primary"):
                if not pasted_text.strip():
                    st.warning("Data kosong!")
                else:
                    existing = {d["Link"] for d in st.session_state.data}
                    baru, skipped = parse_csv_content(pasted_text, existing)
                    st.session_state.data.extend(baru)
                    st.session_state.last_processed = baru
                    st.success(f"Berhasil: {len(baru)} | Duplikat: {skipped}")

        with c2:
            if st.button("📤 Kirim ke Google Sheets", use_container_width=True):
                if not st.session_state.last_processed:
                    st.warning("Tidak ada data baru untuk dikirim.")
                else:
                    with st.spinner("Mengirim data..."):
                        send_to_gsheet(st.session_state.last_processed)
                        st.balloons()
                        st.success("Data berhasil masuk ke Google Sheets!")

        with c3:
            if st.button("🗑️ Reset", use_container_width=True):
                st.session_state.data = []
                st.session_state.last_processed = []
                st.rerun()

    with col_right:
        st.markdown("### 🔑 Akses Google")
        with st.container(border=True):
            st.write("Pastikan Sheet di-share ke:")
            st.code(st.secrets["gcp_service_account"]["client_email"], language="text")
            st.caption("Role: **Editor**")

    st.divider()
    
    if st.session_state.data:
        st.markdown("### 🔍 Preview Data")
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Export to CSV", df.to_csv(index=False), "data_ig.csv", "text/csv")

# =======================
# TAB 2 - DASHBOARD (Full Width)
# =======================
with tab2:
    st.components.v1.iframe(src=LOOKER_EMBED_URL, height=800, scrolling=True)

# =======================
# TAB 3 - PANDUAN (Visual)
# =======================
with tab3:
    st.markdown("## 📘 Panduan Penggunaan InstaMon")
    
    # Diagram Alur Kerja Sederhana
    st.markdown("""
    
    """)

    st.info("**Langkah Singkat:** Login IG → Buka Postingan → Klik Bookmarklet → Paste di Tab Rekap → Klik Proses & Kirim.")

    with st.expander("🛠️ Cara Setting Bookmarklet (Hanya Sekali)"):
        st.markdown("""
        1. Buka Chrome **Bookmark Manager** (Ctrl+Shift+O).
        2. Klik titik tiga di pojok kanan atas -> **Add new bookmark**.
        3. Masukkan Nama: `IG TO CSV`.
        4. Masukkan URL dengan kode di bawah ini:
        """)
        st.code("""javascript:(()=>{const permalink=location.href.split("?")[0]; let captionFull=document.querySelector("h1")?.innerText?.trim()||""; if(!captionFull){const og=document.querySelector('meta[property="og:description"]')?.content||""; captionFull=og.includes(":")?og.split(":").slice(1).join(":").trim():og.trim()} const timeEl=document.querySelector("article time[datetime]")||document.querySelector("time[datetime]"); const timestamp=timeEl?timeEl.getAttribute("datetime"):""; const firstSentence=(t)=>{const m=(t||"").match(/^(.+?[.!?])(\s|$)/s); return m?m[1].trim():(t||"").split("\\n")[0].trim()}; const clean=(t)=>firstSentence(t).replace(/\\s+/g," ").replace(/[^\x00-\x7F]/g,"").replace(/[^A-Za-z0-9 ,\\.?!]+/g," ").trim(); const cap=clean(captionFull).replaceAll('"','""'); const line=`"${permalink}","${cap}","${timestamp}"`; navigator.clipboard.writeText(line).then(()=>alert("✅ Data Disalin!")).catch(()=>prompt("Copy manual:",line));})();""", language="javascript")
