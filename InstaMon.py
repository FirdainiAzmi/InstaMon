import streamlit as st
import pandas as pd
import csv
import re
from datetime import datetime
from io import StringIO
import traceback

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
    st.markdown("""
    <h1 style='text-align:center'>📊 InstaMon BPS</h1>
    <p style='text-align:center; color:gray'>
    Sistem Monitoring Konten Instagram
    </p>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        with st.container(border=True):
            st.markdown("### 🔐 Login Sistem")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if st.button("Masuk", use_container_width=True):
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
    hasil, skipped = [], 0

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

    ws = client.open_by_key(
        st.secrets["gsheet"]["spreadsheet_id"]
    ).worksheet(
        st.secrets["gsheet"]["sheet_name"]
    )

    if not ws.acell("B1").value:
        ws.update("B1:E1", [["Caption", "Tanggal", "", "Link"]])

    start_row = len(ws.get_all_values()) + 1
    values = [[r["Caption"], r["Tanggal"], "", r["Link"]] for r in rows]

    ws.update(f"B{start_row}:E{start_row+len(values)-1}", values)

# =========================================================
# UI TABS
# =========================================================
tab1, tab2, tab3 = st.tabs([
    "🛠️ Rekap Data",
    "📊 Dashboard Monitoring",
    "📘 Informasi Penggunaan"
])

# =========================================================
# TAB 1 — REKAP DATA
# =========================================================
with tab1:
    st.markdown("## 🛠️ Rekap Konten Instagram")
    st.caption("Input manual hasil bookmarklet Instagram")

    c1, c2 = st.columns([2, 1])

    with c1:
        with st.container(border=True):
            st.markdown("### 📋 Input Data CSV")
            pasted_text = st.text_area(
                "Paste hasil bookmarklet di sini",
                height=220,
                placeholder='"link","caption","timestamp"'
            )

    with c2:
        with st.container(border=True):
            st.markdown("### ℹ️ Informasi Teknis")
            st.info("""
            ✅ Non scraping  
            ✅ Manual input  
            ✅ Aman & audit-friendly
            """)

    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("🚀 Proses Data", use_container_width=True):
            if not pasted_text.strip():
                st.warning("Data masih kosong.")
            else:
                existing_links = {d["Link"] for d in st.session_state.data}
                data_baru, skipped = parse_csv_content(pasted_text, existing_links)
                st.session_state.data.extend(data_baru)
                st.session_state.last_processed = data_baru

                st.success(f"{len(data_baru)} data diproses")
                if skipped:
                    st.warning(f"{skipped} duplikat dilewati")

    with b2:
        if st.button("🗑️ Reset", use_container_width=True):
            st.session_state.data = []
            st.session_state.last_processed = []
            st.success("Data direset")

    with b3:
        if st.button("📤 Kirim ke Sheets", use_container_width=True):
            if not st.session_state.last_processed:
                st.warning("Belum ada data baru")
            else:
                send_to_gsheet(st.session_state.last_processed)
                st.success("Data terkirim")

    st.divider()

    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True)

        st.download_button(
            "⬇️ Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            "instamon.csv",
            "text/csv"
        )
    else:
        st.info("Belum ada data.")

# =========================================================
# TAB 2 — DASHBOARD
# =========================================================
with tab2:
    st.markdown("## 📊 Dashboard Monitoring")
    st.caption("Visualisasi data Instagram berbasis Looker Studio")

    with st.container(border=True):
        st.components.v1.iframe(
            src=LOOKER_EMBED_URL,
            height=750,
            scrolling=True
        )

# =========================================================
# TAB 3 — INFORMASI PENGGUNAAN
# =========================================================
with tab3:
    st.markdown("# 📘 Panduan Penggunaan InstaMon")
    st.divider()

    st.markdown("""
    ### 🧠 Apa itu InstaMon?
    **InstaMon** adalah sistem internal untuk merekap dan memonitor
    konten Instagram secara manual, aman, dan terkontrol.
    """)

    st.divider()

    c1, c2, c3 = st.columns(3)
    c1.info("1️⃣ Klik bookmarklet di postingan IG")
    c2.info("2️⃣ Paste hasil ke InstaMon")
    c3.info("3️⃣ Analisis via Dashboard")

    st.divider()

    st.markdown("## 🔖 Cara Membuat Bookmarklet")
    left, right = st.columns([1, 2])

    with left:
        st.markdown("""
        1. Tampilkan Bookmark Bar (Ctrl+Shift+B)  
        2. Bookmark Manager → Add Bookmark  
        3. Nama: **IG to CSV**  
        4. URL: paste kode di samping  
        5. Simpan
        """)

    with right:
        st.code("""
javascript:(()=>{const permalink=location.href.split("?")[0];
let captionFull=document.querySelector("h1")?.innerText?.trim()||"";
if(!captionFull){
 const og=document.querySelector('meta[property="og:description"]')?.content||"";
 captionFull=og.includes(":")?og.split(":").slice(1).join(":").trim():og.trim()
}
const timeEl=document.querySelector("article time[datetime]")||document.querySelector("time[datetime]");
const timestamp=timeEl?timeEl.getAttribute("datetime"):"";
const clean=t=>t.replace(/\\s+/g," ").replace(/[^\x00-\x7F]/g,"")
.replace(/[^A-Za-z0-9 ,\\.?!]+/g," ").trim();
const line=`"${permalink}","${clean(captionFull)}","${timestamp}"`;
navigator.clipboard.writeText(line)
.then(()=>alert("CSV disalin:\\n"+line));
})();
        """, language="javascript")
