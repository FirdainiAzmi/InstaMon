import streamlit as st
import instaloader
import pandas as pd
import re

st.set_page_config(page_title="InstaMon BPS", layout="wide")

LOOKER_EMBED_URL = "https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF"

if "data" not in st.session_state:
    st.session_state.data = []

def first_sentence(text):
    text = text.strip()
    match = re.search(r"(.+?[.!?])", text)
    return match.group(1) if match else text

def clean_caption(text):
    text = (text or "").replace("\n", " ").replace("\r", " ")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = first_sentence(text)
    text = re.sub(r"[^A-Za-z0-9 ,.!?]+", " ", text)
    text = " ".join(text.split()).strip()
    return text

def scrape_instagram(url):
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        save_metadata=False,
        compress_json=False
    )

    shortcode = url.split("/")[-2]
    post = instaloader.Post.from_shortcode(loader.context, shortcode)

    caption = clean_caption(post.caption or "")
    tanggal = post.date.strftime("%d/%m/%Y")

    return {
        "Caption": caption,
        "Tanggal": tanggal,
        "Link": url
    }

# ==================== STYLE CSS ====================
st.markdown(
    """
    <style>
    /* Background container untuk tab input dan tabel */
    .blue-container {
        background-color: #E6F0FA;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid #B0C4DE;
    }

    /* Judul utama */
    .title-blue {
        color: #0B3D91;
        font-size: 36px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 10px;
    }

    /* Subjudul */
    .subtitle-blue {
        color: #0B3D91;
        font-size: 20px;
        font-weight: 600;
        margin-bottom: 10px;
    }

    /* Tombol biru */
    .stButton>button {
        background-color: #0B3D91;
        color: white;
        border-radius: 8px;
        padding: 0.5em 1em;
        font-weight: bold;
        border: none;
    }

    .stButton>button:hover {
        background-color: #1E5BB8;
        color: white;
    }

    /* Iframe dashboard */
    .iframe-container {
        border: 1px solid #B0C4DE;
        border-radius: 12px;
        padding: 10px;
        background-color: #F0F8FF;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==================== TABS ====================
tab1, tab2 = st.tabs(["🛠️ Tools Input Data", "📊 Dashboard Monitoring"])

# -------------------- TAB 1 --------------------
with tab1:
    st.markdown('<div class="title-blue">🛠️ InstaMon Instagram Scraper</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle-blue">Masukkan link Instagram (1 link per baris)</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="blue-container">', unsafe_allow_html=True)

        links_text = st.text_area(
            "Input link di sini:",
            height=150,
            placeholder="https://www.instagram.com/p/xxxx/\nhttps://www.instagram.com/reel/yyyy/"
        )

        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("🚀 Proses Data"):
                if not links_text.strip():
                    st.warning("⚠️ Link tidak boleh kosong!")
                else:
                    links = [x.strip() for x in links_text.splitlines() if x.strip()]
                    sukses = 0
                    with st.spinner("Mengambil data dari Instagram..."):
                        for link in links:
                            try:
                                hasil = scrape_instagram(link)
                                st.session_state.data.append(hasil)
                                sukses += 1
                            except:
                                st.error(f"Gagal mengambil: {link}")
                    st.success(f"✅ {sukses} data berhasil diproses!")

        with col2:
            if st.button("🗑️ Reset Data"):
                st.session_state.data = []
                st.success("✅ Semua data berhasil dihapus!")

        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("📋 Tabel Hasil Scraping")
    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            csv,
            "hasil_scraping_instagram.csv",
            "text/csv",
            key="download-csv"
        )
    else:
        st.info("Belum ada data yang diproses.")

# -------------------- TAB 2 --------------------
with tab2:
    st.markdown('<div class="title-blue">📊 Dashboard Monitoring</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle-blue">Pantau hasil scraping melalui dashboard berikut:</div>', unsafe_allow_html=True)

    if LOOKER_EMBED_URL.strip() == "":
        st.warning("Dashboard belum ditautkan.")
    else:
        st.markdown('<div class="iframe-container">', unsafe_allow_html=True)
        st.components.v1.iframe(
            src=LOOKER_EMBED_URL,
            width=1200,
            height=650,
            scrolling=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
