import streamlit as st
import instaloader
import pandas as pd
import re
import time

st.set_page_config(page_title="InstaMon BPS", layout="wide")

LOOKER_EMBED_URL = "https://lookerstudio.google.com/embed/reporting/f8d6fc1b-b5bd-43eb-881c-e74a9d86ff75/page/Z52hF"

# ==================== SESSION ====================
if "data" not in st.session_state:
    st.session_state.data = []

# ==================== INSTALOADER (SATU KALI) ====================
loader = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    save_metadata=False,
    compress_json=False,
    quiet=True
)

# ==================== FUNGSI ====================
def first_sentence(text):
    text = text.strip()
    match = re.search(r"(.+?[.!?])", text)
    return match.group(1) if match else text

def clean_caption(text):
    text = (text or "").replace("\n", " ").replace("\r", " ")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = first_sentence(text)
    text = re.sub(r"[^A-Za-z0-9 ,.!?]+", " ", text)
    return " ".join(text.split()).strip()

def scrape_instagram(url):
    shortcode = url.rstrip("/").split("/")[-1]
    post = instaloader.Post.from_shortcode(loader.context, shortcode)

    return {
        "Caption": clean_caption(post.caption or ""),
        "Tanggal": post.date.strftime("%d/%m/%Y"),
        "Link": url
    }

# ==================== UI ====================
tab1, tab2 = st.tabs(["🛠️ Tools Input Data", "📊 Dashboard Monitoring"])

with tab1:
    st.title("🛠️ InstaMon Instagram Scraper (No Login)")

    st.warning(
        "⚠️ Mode TANPA LOGIN\n"
        "- Maksimal 5 link per proses\n"
        "- Delay 7 detik / link\n"
        "- Beberapa post bisa gagal (normal)"
    )

    links_text = st.text_area(
        "Masukkan link Instagram (1 per baris)",
        height=150,
        placeholder="https://www.instagram.com/p/xxxx/"
    )

    if st.button("🚀 Proses Data"):
        links = [l.strip() for l in links_text.splitlines() if l.strip()]

        if len(links) > 5:
            st.error("❌ Maksimal 5 link per proses untuk menghindari blokir")
        else:
            sukses, gagal = 0, 0
            with st.spinner("Scraping Instagram (slow & safe mode)..."):
                for i, link in enumerate(links, start=1):
                    try:
                        hasil = scrape_instagram(link)
                        st.session_state.data.append(hasil)
                        sukses += 1
                        st.info(f"✅ ({i}/{len(links)}) Berhasil")
                    except Exception as e:
                        gagal += 1
                        st.warning(f"⚠️ ({i}/{len(links)}) Gagal: {link}")
                    time.sleep(7)  # ⬅️ DELAY AMAN

            st.success(f"🎉 Selesai | Berhasil: {sukses} | Gagal: {gagal}")

    st.divider()

    if st.session_state.data:
        df = pd.DataFrame(st.session_state.data)
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            csv,
            "hasil_scraping_instagram.csv",
            "text/csv"
        )

with tab2:
    st.title("📊 Dashboard Monitoring")
    st.components.v1.iframe(
        src=LOOKER_EMBED_URL,
        width=1200,
        height=650
    )
