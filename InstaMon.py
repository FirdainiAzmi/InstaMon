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
# 1. CONFIG & STYLE (TAMPILAN PREMIUM VERSI 2)
# =========================================================
st.set_page_config(
    page_title="InstaMon BPS",
    layout="wide",
    page_icon="📊"
)

st.markdown("""
    <style>
    /* Global Background */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Header Styling */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        color: #1E293B;
    }

    /* Card Styling */
    div[data-testid="stExpander"], div[data-container="true"] {
        background-color: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 10px 10px 0px 0px;
        padding: 10px 20px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4F46E5 !important;
        color: white !important;
    }

    /* Button Styling */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(45deg, #4F46E5, #7C3AED);
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

LOOKER_EMBED_URL = "https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF"

# =========================================================
# 2. SESSION STATE (LOGIKA ASLI)
# =========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "data" not in st.session_state:
    st.session_state.data = []
if "last_processed" not in st.session_state:
    st.session_state.last_processed = []

# =========================================================
# 3. LOGIN PAGE (TAMPILAN PREMIUM)
# =========================================================
def login_page():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("#")
        with st.container(border=True):
            st.image("https://img.icons8.com/fluency/96/instagram-new.png", width=60)
            st.title("🔐 Login InstaMon")
            st.caption("Aplikasi Monitoring Konten BPS")
            
            username = st.text_input("Username", placeholder="Masukkan username")
            password = st.text_input("Password", type="password", placeholder="Masukkan password")

            if st.button("Login Sekarang 🚀", use_container_width=True, type="primary"):
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
# 4. HELPER FUNCTIONS (LOGIKA ASLI)
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
# 5. UI TABS (TAMPILAN PREMIUM VERSI 2)
# =========================================================
st.title("📊 InstaMon BPS")
st.markdown("Automasi Monitoring Konten Instagram")

tab1, tab2, tab3 = st.tabs([
    "🛠️ Rekap Data", 
    "📊 Dashboard Monitoring", 
    "📘 Informasi Penggunaan"
])

# --- TAB 1: REKAP DATA ---
with tab1:
    st.markdown("### 🛠️ Input & Proses Data")
    
    col_main, col_side = st.columns([2, 1])
    
    with col_main:
        with st.container(border=True):
            pasted_text = st.text_area(
                "📋 Paste Data CSV dari Bookmarklet",
                height=220,
                placeholder="Tempel hasil copy di sini..."
            )
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🚀 Proses Data", use_container_width=True, type="primary"):
                    if not pasted_text.strip():
                        st.warning("Paste data terlebih dahulu.")
                    else:
                        existing_links = {d["Link"] for d in st.session_state.data}
                        data_baru, skipped = parse_csv_content(pasted_text, existing_links)
                        st.session_state.data.extend(data_baru)
                        st.session_state.last_processed = data_baru
                        st.success(f"✅ {len(data_baru)} data diproses")
                        if skipped > 0: st.warning(f"⚠️ {skipped} data dilewati (duplikat)")
            
            with c2:
                if st.button("📤 Kirim ke GSheet", use_container_width=True):
                    rows = st.session_state.last_processed
                    if not rows: st.warning("Belum ada data baru.")
                    else:
                        with st.spinner("Mengirim ke Google Sheets..."):
                            send_to_gsheet(rows)
                            st.success(f"✅ {len(rows)} baris terkirim!")
                            st.balloons()
            
            with c3:
                if st.button("🗑️ Reset Antrean", use_container_width=True):
                    st.session_state.data = []
                    st.session_state.last_processed = []
                    st.rerun()

    with col_side:
        with st.expander("🔐 Akun Google Sheets", expanded=True):
            st.caption("Share Sheet ke email ini:")
            st.code(st.secrets["gcp_service_account"]["client_email"])
            st.info("Pastikan Sheet memiliki kolom: Caption (B), Tanggal (C), Link (E)")

    st.divider()
    
    if st.session_state.data:
        st.markdown("### 🔍 Preview Data")
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode("utf-8"), "rekap_ig.csv", "text/csv")
    else:
        st.info("Belum ada data untuk ditampilkan.")

# --- TAB 2: DASHBOARD ---
with tab2:
    st.markdown("### 📊 Dashboard Monitoring")
    st.components.v1.iframe(src=LOOKER_EMBED_URL, width=None, height=720, scrolling=True)

# --- TAB 3: PANDUAN ---
with tab3:
    st.markdown("## 📘 Panduan Penggunaan InstaMon")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("**1️⃣ Bookmarklet**\nKlik 'IG to CSV' di browser saat membuka postingan.")
    with c2:
        st.info("**2️⃣ Rekap Data**\nPaste di kolom input lalu klik tombol Proses & Kirim.")
    with c3:
        st.info("**3️⃣ Dashboard**\nData akan muncul otomatis di tab Dashboard.")

    st.divider()
    
    col_l, col_r = st.columns([1, 2])
    with col_l:
        st.markdown("### 🔖 Buat Bookmarklet")
        st.write("1. Buka Bookmark Manager\n2. Add New Bookmark\n3. Nama: `IG to CSV`\n4. URL: Paste kode JS samping.")
    
    with col_r:
        st.code("""javascript:(()=>{const permalink=location.href.split("?")[0]; let captionFull=document.querySelector("h1")?.innerText?.trim()||""; if(!captionFull){const og=document.querySelector('meta[property="og:description"]')?.content||""; captionFull=og.includes(":")?og.split(":").slice(1).join(":").trim():og.trim()} const timeEl=document.querySelector("article time[datetime]")||document.querySelector("time[datetime]"); const timestamp=timeEl?timeEl.getAttribute("datetime"):""; const firstSentence=(t)=>{const m=(t||"").match(/^(.+?[.!?])(\s|$)/s); return m?m[1].trim():(t||"").split("\\n")[0].trim()}; const clean=(t)=>firstSentence(t).replace(/\\s+/g," ").replace(/[^\x00-\x7F]/g,"").replace(/[^A-Za-z0-9 ,\\.?!]+/g," ").trim(); const cap=clean(captionFull).replaceAll('"','""'); const line=`"${permalink}","${cap}","${timestamp}"`; navigator.clipboard.writeText(line).then(()=>alert("CSV disalin:\\n"+line)).catch(()=>prompt("Copy CSV:",line));})();""", language="javascript")

st.markdown("---")
st.caption("InstaMon BPS v2.0 • Built with ❤️ for better monitoring")
