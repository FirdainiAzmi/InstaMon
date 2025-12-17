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
# 🎨 CONFIG & PREMIUM STYLING (VERSI 2)
# =========================================================
st.set_page_config(
    page_title="InstaMon BPS",
    layout="wide",
    page_icon="📊"
)

# Custom CSS untuk tampilan Dashboard Modern
st.markdown("""
    <style>
    /* Mengubah font ke Inter/Jakarta Sans agar modern */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Gradient Background untuk seluruh aplikasi */
    .stApp {
        background: linear-gradient(135deg, #f8faff 0%, #eef2f7 100%);
    }

    /* Glassmorphism Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    [data-testid="stSidebar"] .stMarkdown h2, [data-testid="stSidebar"] .stMarkdown p {
        color: white !important;
    }

    /* Container Card Style */
    div[data-testid="stExpander"], div.stContainer {
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.06);
        border: 1px solid #e2e8f0;
        padding: 10px;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9;
        border-radius: 8px 8px 0px 0px;
        padding: 8px 20px;
        font-weight: 600;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }

    /* Button Styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        border: none;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)

LOOKER_EMBED_URL = "https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF"

# =========================================================
# 🔄 SESSION STATE (LOGIKA ASLI)
# =========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "data" not in st.session_state:
    st.session_state.data = []
if "last_processed" not in st.session_state:
    st.session_state.last_processed = []

# =========================================================
# 🔐 LOGIN PAGE (DESAIN PREMIUM)
# =========================================================
def login_page():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.write("#")
        with st.container():
            st.markdown("<h2 style='text-align: center;'>🔐 InstaMon BPS</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray;'>Internal Content Monitoring System</p>", unsafe_allow_html=True)
            st.write("---")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Masuk Ke Dashboard", use_container_width=True, type="primary"):
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
# 🛠️ HELPER FUNCTIONS (LOGIKA ASLI)
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
        ts = ts.strip()
        if ts.endswith("Z"): ts = ts.replace("Z", "+00:00")
        tanggal = datetime.fromisoformat(ts).strftime("%m-%d-%Y")
        hasil.append({
            "Caption": clean_caption(caption),
            "Tanggal": tanggal,
            "Link": link
        })
    return hasil, skipped

def send_to_gsheet(rows):
    sa_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(sa_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    spreadsheet_id = st.secrets["gsheet"]["spreadsheet_id"]
    sheet_name = st.secrets["gsheet"]["sheet_name"]
    ws = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    if (ws.acell("B1").value or "") == "": ws.update("B1", [["Caption"]])
    if (ws.acell("C1").value or "") == "": ws.update("C1", [["Tanggal"]])
    if (ws.acell("E1").value or "") == "": ws.update("E1", [["Link"]])
    last_row = len(ws.get_all_values())
    start_row = max(2, last_row + 1)
    end_row = start_row + len(rows) - 1
    values = [[r["Caption"], r["Tanggal"], "", r["Link"]] for r in rows]
    ws.update(f"B{start_row}:E{end_row}", values, value_input_option="RAW")

# =========================================================
# 📂 SIDEBAR NAVIGATION
# =========================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/combo-chart.png", width=80)
    st.markdown("## Navigasi")
    st.write("Pilih halaman:")
    # Navigasi menggunakan radio button agar lebih clean
    page = st.radio("Go to", ["Rekap Data", "Dashboard", "Panduan"], label_visibility="collapsed")
    
    st.write("---")
    st.markdown("### 🟢 Status Koneksi")
    st.caption(f"Google Sheets: **{st.secrets['gsheet']['sheet_name']}**")
    
    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# =========================================================
# 🚀 MAIN CONTENT
# =========================================================

# --- HALAMAN 1: REKAP DATA ---
if page == "Rekap Data":
    st.title("🛠️ Rekap Data Instagram")
    st.markdown("Proses data CSV dari bookmarklet ke Google Sheets secara otomatis.")

    col_input, col_stats = st.columns([2, 1])
    
    with col_input:
        with st.container():
            pasted_text = st.text_area("📋 Paste Data CSV Di Sini", height=220, placeholder="link, caption, timestamp...")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🚀 Proses Data", use_container_width=True, type="primary"):
                    if not pasted_text.strip():
                        st.warning("Data masih kosong.")
                    else:
                        existing_links = {d["Link"] for d in st.session_state.data}
                        data_baru, skipped = parse_csv_content(pasted_text, existing_links)
                        st.session_state.data.extend(data_baru)
                        st.session_state.last_processed = data_baru
                        st.success(f"Berhasil: {len(data_baru)} baris")
                        if skipped > 0: st.info(f"Duplikat: {skipped} dilewati")
            
            with c2:
                if st.button("📤 Kirim ke GSheets", use_container_width=True):
                    if not st.session_state.last_processed:
                        st.warning("Belum ada data baru.")
                    else:
                        send_to_gsheet(st.session_state.last_processed)
                        st.balloons()
                        st.success("Data terkirim ke Google Sheets!")
            
            with c3:
                if st.button("🗑️ Reset Antrean", use_container_width=True):
                    st.session_state.data = []
                    st.session_state.last_processed = []
                    st.rerun()

    with col_stats:
        with st.container():
            st.markdown("### 📊 Statistik")
            st.metric("Data Dalam Antrean", len(st.session_state.data))
            st.metric("Data Terakhir Diproses", len(st.session_state.last_processed))
            with st.expander("🔑 Email Service Account"):
                st.code(st.secrets["gcp_service_account"]["client_email"])

    st.write("---")
    if st.session_state.data:
        st.markdown("### 🔍 Preview Antrean")
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode("utf-8"), "rekap.csv", "text/csv")
    else:
        st.info("Antrean kosong. Silahkan paste data untuk memulai.")

# --- HALAMAN 2: DASHBOARD ---
elif page == "Dashboard":
    st.title("📊 Dashboard Monitoring")
    st.markdown("Visualisasi data yang telah dikirim ke Google Sheets.")
    st.components.v1.iframe(src=LOOKER_EMBED_URL, height=800, scrolling=True)

# --- HALAMAN 3: PANDUAN ---
elif page == "Panduan":
    st.title("📘 Panduan Penggunaan")
    
    st.markdown("### 🔄 Alur Kerja InstaMon")
    

    st.info("**Tip:** Gunakan shortcut `Ctrl + V` untuk menempel data dengan cepat di area input.")

    st.markdown("#### 🔖 Cara Membuat Bookmarklet")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        st.markdown("""
        1. Tampilkan Bookmark Bar (`Ctrl+Shift+B`).
        2. Klik kanan > **Bookmark Manager**.
        3. Klik **Add New Bookmark**.
        4. Nama: `IG to CSV`.
        5. URL: Paste kode di samping.
        """)
    with col_r:
        st.code("""javascript:(()=>{const permalink=location.href.split("?")[0]; let captionFull=document.querySelector("h1")?.innerText?.trim()||""; if(!captionFull){const og=document.querySelector('meta[property="og:description"]')?.content||""; captionFull=og.includes(":")?og.split(":").slice(1).join(":").trim():og.trim()} const timeEl=document.querySelector("article time[datetime]")||document.querySelector("time[datetime]"); const timestamp=timeEl?timeEl.getAttribute("datetime"):""; const firstSentence=(t)=>{const m=(t||"").match(/^(.+?[.!?])(\s|$)/s); return m?m[1].trim():(t||"").split("\\n")[0].trim()}; const clean=(t)=>firstSentence(t).replace(/\\s+/g," ").replace(/[^\x00-\x7F]/g,"").replace(/[^A-Za-z0-9 ,\\.?!]+/g," ").trim(); const cap=clean(captionFull).replaceAll('"','""'); const line=`"${permalink}","${cap}","${timestamp}"`; navigator.clipboard.writeText(line).then(()=>alert("CSV disalin:\\n"+line)).catch(()=>prompt("Copy CSV:",line));})();""", language="javascript")
