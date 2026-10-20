
import os
import re
from pathlib import Path

import boto3
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from botocore.config import Config
from dotenv import load_dotenv
from wordcloud import WordCloud


# ==================================================
# 1. KONFIGURASI
# ==================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / "minio.env")

ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9002")
ACCESS_KEY = os.getenv("MINIO_ROOT_USER")
SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD")
BUCKET = "sibi-books"

st.set_page_config(
    page_title="SIBI Word Frequency",
    page_icon="📚",
    layout="wide"
)


@st.cache_resource
def get_client():
    if not ACCESS_KEY or not SECRET_KEY:
        raise ValueError(
            "MINIO_ROOT_USER atau MINIO_ROOT_PASSWORD "
            "belum tersedia di minio.env."
        )

    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"}
        ),
        region_name="us-east-1"
    )


def list_output_folders(client):
    response = client.list_objects_v2(
        Bucket=BUCKET,
        Prefix="output/",
        Delimiter="/"
    )
    return sorted(
        item["Prefix"]
        for item in response.get("CommonPrefixes", [])
    )


@st.cache_data(ttl=60)
def load_counts(prefix):
    client = get_client()
    paginator = client.get_paginator("list_objects_v2")
    rows = []

    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for item in page.get("Contents", []):
            filename = item["Key"].rsplit("/", 1)[-1]

            if not filename.startswith("part-"):
                continue

            body = client.get_object(
                Bucket=BUCKET,
                Key=item["Key"]
            )["Body"].read().decode("utf-8", errors="replace")

            for line in body.splitlines():
                parts = line.split("\t", 1)

                if len(parts) != 2:
                    continue

                word = parts[0].strip()

                try:
                    count = int(parts[1].strip())
                except ValueError:
                    continue

                if word and count >= 0:
                    rows.append((word, count))

    if not rows:
        return pd.DataFrame(columns=["Kata", "Frekuensi"])

    df = pd.DataFrame(rows, columns=["Kata", "Frekuensi"])
    return (
        df.groupby("Kata", as_index=False)["Frekuensi"]
        .sum()
        .sort_values("Frekuensi", ascending=False)
        .reset_index(drop=True)
    )


def output_info(prefix):
    """Pisahkan identitas buku dari versi hasil analisis."""
    name = prefix.rstrip("/").split("/")[-1]
    name = re.sub(r"^wordcount_", "", name)
    name = re.sub(r"_clean_v\d+$", "", name)
    name = re.sub(r"_v\d+$", "", name)

    title = name.replace("_", " ").strip().title()
    is_clean = "_clean_v" in prefix.rstrip("/")

    return title or name, is_clean


def short_title(prefix):
    return output_info(prefix)[0]


def format_number(number):
    return f"{int(number):,}"


# ==================================================
# 2. HEADER DAN KONEKSI
# ==================================================

st.title("Analisis Frekuensi Kata Buku Digital SIBI")
st.caption(
    "MinIO Object Storage · Hadoop MapReduce · Streamlit"
)

with st.sidebar:
    st.header("Pengaturan")

    if st.button("Muat ulang data", use_container_width=True):
        load_counts.clear()
        list_output_folders.clear()
        st.rerun()

    st.caption("Sumber data: bucket sibi-books")

try:
    client = get_client()
    client.head_bucket(Bucket=BUCKET)
    folders = list_output_folders(client)

except Exception as exc:
    st.error("Koneksi ke MinIO gagal. Periksa container dan kredensial.")
    st.code(str(exc))
    st.stop()

if not folders:
    st.warning("Belum ada hasil MapReduce di folder output/.")
    st.stop()


# Prioritaskan hasil clean jika tersedia.
clean_folders = [
    f for f in folders
    if "_clean_v" in f.rstrip("/")
]

default_folder = clean_folders[-1] if clean_folders else folders[-1]

selected = st.selectbox(
    "Pilih hasil analisis",
    folders,
    index=folders.index(default_folder),
    format_func=lambda f: f.rstrip("/").split("/")[-1]
)

try:
    df = load_counts(selected)
except Exception as exc:
    st.error("Gagal membaca file hasil dari MinIO.")
    st.code(str(exc))
    st.stop()

if df.empty:
    st.warning("Tidak ada data kata pada hasil yang dipilih.")
    st.stop()


# ==================================================
# 3. RINGKASAN
# ==================================================

total_tokens = int(df["Frekuensi"].sum())
unique_words = int(df["Kata"].nunique())
top_word = str(df.iloc[0]["Kata"])
top_frequency = int(df.iloc[0]["Frekuensi"])

st.subheader("Ringkasan Analisis")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total kemunculan kata", format_number(total_tokens))
c2.metric("Kata unik", format_number(unique_words))
c3.metric("Kata paling sering", top_word)
c4.metric("Frekuensi tertinggi", format_number(top_frequency))

st.caption(f"Hasil yang digunakan: `{selected}`")


# ==================================================
# 4. WORD CLOUD
# ==================================================

st.divider()
st.subheader("1. Word Cloud Berdasarkan Frekuensi")

st.write(
    "Ukuran setiap kata merepresentasikan frekuensi kemunculannya. "
    "Kata yang lebih besar muncul lebih sering dalam teks."
)

frequencies = dict(zip(df["Kata"], df["Frekuensi"]))

cloud = WordCloud(
    width=1200,
    height=600,
    background_color="white",
    collocations=False
).generate_from_frequencies(frequencies)

fig, ax = plt.subplots(figsize=(14, 6))
ax.imshow(cloud, interpolation="bilinear")
ax.axis("off")
st.pyplot(fig)
plt.close(fig)


# ==================================================
# 5. GRAFIK BATANG INTERAKTIF
# ==================================================

st.divider()
st.subheader("2. Kata dengan Frekuensi Tertinggi")

max_words = st.slider(
    "Jumlah kata yang ditampilkan",
    min_value=5,
    max_value=min(50, len(df)),
    value=min(20, len(df)),
    key="top_words_slider"
)

top_df = df.head(max_words).sort_values("Frekuensi")

fig, ax = plt.subplots(figsize=(11, max(5, max_words * 0.3)))
ax.barh(top_df["Kata"], top_df["Frekuensi"])
ax.set_xlabel("Frekuensi")
ax.set_ylabel("Kata")
ax.set_title(f"{max_words} Kata dengan Frekuensi Tertinggi")
ax.grid(axis="x", alpha=0.25)
ax.set_axisbelow(True)
fig.tight_layout()
st.pyplot(fig)
plt.close(fig)

st.dataframe(
    df.head(max_words),
    use_container_width=True,
    hide_index=True
)


# ==================================================
# 6. INTERPRETASI OTOMATIS
# ==================================================

st.divider()
st.subheader("3. Interpretasi Hasil")

top_share = top_frequency / total_tokens * 100 if total_tokens else 0
top_five_share = (
    df.head(5)["Frekuensi"].sum() / total_tokens * 100
    if total_tokens else 0
)

st.markdown(
    f"""
    - **Kata dominan:** `{top_word}` muncul sebanyak
      **{format_number(top_frequency)} kali**, atau sekitar
      **{top_share:.2f}%** dari seluruh kemunculan kata yang dihitung.
    - **Keragaman kosakata:** ditemukan
      **{format_number(unique_words)} kata unik** dengan total
      **{format_number(total_tokens)} kemunculan kata**.
    - **Konsentrasi frekuensi:** lima kata teratas menyumbang sekitar
      **{top_five_share:.2f}%** dari seluruh kemunculan kata.
    """
)

st.info(
    "Interpretasi ini menggambarkan pola frekuensi, bukan otomatis "
    "menentukan tema atau makna buku. Makna kata dominan perlu "
    "ditinjau bersama konteks kalimat dan isi buku."
)


# ==================================================
# 7. PERBANDINGAN ANTARJUDUL BUKU
# ==================================================

st.divider()
st.subheader("4. Perbandingan Antarjudul Buku")

# Kelompokkan hasil berdasarkan nama buku, bukan versi raw/clean.
# Jika tersedia beberapa versi, prioritaskan clean.
book_outputs = {}

for folder in folders:
    title, is_clean = output_info(folder)

    if title not in book_outputs:
        book_outputs[title] = folder
    elif is_clean:
        book_outputs[title] = folder

if len(book_outputs) < 2:
    st.info(
        "Perbandingan antarjudul akan tersedia setelah hasil MapReduce "
        "dari minimal dua buku berbeda tersimpan di MinIO. "
        "Saat ini baru tersedia satu judul buku yang dapat dibandingkan."
    )
else:
    titles = sorted(book_outputs.keys())

    compare_titles = st.multiselect(
        "Pilih buku yang ingin dibandingkan",
        options=titles,
        default=titles[:min(3, len(titles))]
    )

    if len(compare_titles) < 2:
        st.warning("Pilih minimal dua judul buku.")
    else:
        summary_rows = []
        comparison = {}

        for title in compare_titles:
            book_df = load_counts(book_outputs[title])

            if book_df.empty:
                continue

            summary_rows.append({
                "Judul buku": title,
                "Total kemunculan kata": int(book_df["Frekuensi"].sum()),
                "Kata unik": int(book_df["Kata"].nunique()),
                "Kata paling sering": str(book_df.iloc[0]["Kata"]),
                "Frekuensi tertinggi": int(book_df.iloc[0]["Frekuensi"])
            })

            comparison[title] = book_df.set_index("Kata")["Frekuensi"]

        if summary_rows:
            summary_df = pd.DataFrame(summary_rows)
            st.dataframe(
                summary_df,
                use_container_width=True,
                hide_index=True
            )

            # Bandingkan 10 kata teratas dari seluruh buku terpilih.
            all_top_words = set()

            for book_df in comparison.values():
                all_top_words.update(book_df.nlargest(10).index)

            plot_df = pd.DataFrame({
                title: series.reindex(
                    sorted(all_top_words), fill_value=0
                )
                for title, series in comparison.items()
            })

            st.write("**Perbandingan frekuensi kata**")
            st.bar_chart(plot_df, use_container_width=True)

            st.caption(
                "Kata yang tidak muncul pada suatu buku ditampilkan "
                "dengan frekuensi nol. Perbandingan bermakna jika "
                "proses ekstraksi dan preprocessing antarbuku konsisten."
            )


# ==================================================
# 8. UNDUH HASIL
# ==================================================

st.divider()

csv_data = df.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "Unduh tabel frekuensi sebagai CSV",
    data=csv_data,
    file_name="frekuensi_kata_sibi.csv",
    mime="text/csv"
)
