
import os
import re
import sys
import time
import logging
import subprocess
from pathlib import Path

import boto3
import pymupdf

from botocore.config import Config
from dotenv import load_dotenv


# ==================================================
# CONFIGURATION
# ==================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
STAGING_DIR = PROJECT_DIR / "data" / "staging"
MAPREDUCE_DIR = PROJECT_DIR / "mapreduce"

STAGING_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(PROJECT_DIR / "minio.env")

ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9002")
ACCESS_KEY = os.getenv("MINIO_ROOT_USER")
SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD")

BUCKET = "sibi-books"
NAMENODE = "sibi-namenode"
HADOOP = "/opt/hadoop-3.2.1/bin/hadoop"
STREAMING_JAR = (
    "/opt/hadoop-3.2.1/share/hadoop/tools/lib/"
    "hadoop-streaming-3.2.1.jar"
)

POLL_SECONDS = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# ==================================================
# MINIO CONNECTION
# ==================================================

def get_client():
    if not ACCESS_KEY or not SECRET_KEY:
        raise RuntimeError(
            "Kredensial MinIO tidak ditemukan di minio.env."
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


def list_pdf_objects(client):
    """Cari PDF di root bucket, bukan di folder extracted/output."""
    pdfs = []
    paginator = client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=BUCKET):
        for item in page.get("Contents", []):
            key = item["Key"]

            if (
                key.lower().endswith(".pdf")
                and "/" not in key
            ):
                pdfs.append(key)

    return sorted(pdfs)


# ==================================================
# FILE NAMING
# ==================================================

def make_slug(key):
    stem = Path(key).stem.lower()

    # Buang suffix metadata judul buku jika ada.
    stem = re.sub(r"[-_ ]bs[-_ ]kls[-_ ]x$", "", stem)
    stem = re.sub(r"[-_ ]kelas[-_ ]x$", "", stem)

    stem = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")

    # Pertahankan nama output yang sudah digunakan
    # untuk buku pertama dalam proyek.
    if stem.startswith("dasar_teknika_kapal_penangkap_ikan"):
        return "dasar_teknika"

    return stem


def output_prefix(key):
    slug = make_slug(key)
    return f"output/wordcount_{slug}_clean_v1/"


def object_exists(client, key):
    response = client.list_objects_v2(
        Bucket=BUCKET,
        Prefix=key,
        MaxKeys=1
    )
    return bool(response.get("Contents"))


# ==================================================
# PDF EXTRACTION
# ==================================================

def extract_pdf(pdf_path, txt_path):
    total_chars = 0
    total_pages = 0

    with pymupdf.open(pdf_path) as document:
        with open(txt_path, "w", encoding="utf-8") as output:
            for page_number, page in enumerate(document, start=1):
                text = page.get_text("text")

                output.write(text)
                output.write("\n")

                total_chars += len(text.strip())
                total_pages += 1

    if total_pages == 0:
        raise RuntimeError("PDF tidak memiliki halaman.")

    if total_chars == 0:
        raise RuntimeError(
            "Tidak ditemukan teks yang dapat diekstrak. "
            "PDF mungkin berupa hasil scan dan membutuhkan OCR."
        )

    return total_pages, total_chars


# ==================================================
# HADOOP MAPREDUCE
# ==================================================

def prepare_hadoop_scripts():
    """Salin mapper, reducer, dan stopword ke container NameNode."""
    required_files = [
        MAPREDUCE_DIR / "mapper_clean.py",
        MAPREDUCE_DIR / "reducer.py",
        MAPREDUCE_DIR / "stopwords_id.txt",
    ]

    for path in required_files:
        if not path.is_file():
            raise FileNotFoundError(
                f"File MapReduce tidak ditemukan: {path}"
            )

        subprocess.run(
            ["docker", "cp", str(path), f"{NAMENODE}:/tmp/{path.name}"],
            check=True
        )


def run_mapreduce(input_key, output_key, job_name):
    command = [
        "docker", "exec", NAMENODE,
        HADOOP, "jar", STREAMING_JAR,
        "-files",
        "/tmp/mapper_clean.py,/tmp/reducer.py,/tmp/stopwords_id.txt",

        "-D", f"mapreduce.job.name={job_name}",
        "-D", "yarn.app.mapreduce.am.resource.mb=256",
        "-D", "yarn.app.mapreduce.am.command-opts=-Xmx192m",
        "-D", "mapreduce.map.memory.mb=256",
        "-D", "mapreduce.map.java.opts=-Xmx192m",
        "-D", "mapreduce.reduce.memory.mb=256",
        "-D", "mapreduce.reduce.java.opts=-Xmx192m",
        "-D", "mapreduce.job.reduces=1",

        "-mapper", "python3 mapper_clean.py",
        "-reducer", "python3 reducer.py",

        "-input", f"s3a://{BUCKET}/{input_key}",
        "-output", f"s3a://{BUCKET}/{output_key}",
    ]

    logging.info("Menjalankan Hadoop MapReduce: %s", job_name)

    subprocess.run(
        command,
        check=True,
        text=True
    )


# ==================================================
# PROCESS ONE PDF
# ==================================================

def process_pdf(client, key):
    target_output = output_prefix(key)

    # Hindari menjalankan ulang buku yang sudah selesai.
    if object_exists(client, target_output):
        logging.info(
            "Lewati %s: output sudah ada di %s",
            key, target_output
        )
        return

    filename = Path(key).name
    local_pdf = STAGING_DIR / filename
    local_txt = STAGING_DIR / f"{Path(filename).stem}.txt"

    extracted_key = (
        f"extracted/{Path(filename).stem}.txt"
    )

    logging.info("Mulai memproses PDF: %s", key)

    # 1. Download PDF dari MinIO.
    client.download_file(BUCKET, key, str(local_pdf))

    # 2. Ekstrak PDF dengan PyMuPDF.
    pages, characters = extract_pdf(local_pdf, local_txt)

    logging.info(
        "Ekstraksi berhasil: %s halaman, %s karakter",
        pages, characters
    )

    # 3. Upload teks hasil ekstraksi ke MinIO.
    client.upload_file(
        str(local_txt),
        BUCKET,
        extracted_key,
        ExtraArgs={"ContentType": "text/plain; charset=utf-8"}
    )

    logging.info(
        "Teks tersimpan: s3://%s/%s",
        BUCKET, extracted_key
    )

    # 4. Pastikan skrip tersedia di container.
    prepare_hadoop_scripts()

    # 5. Jalankan Word Count + stopword removal.
    job_name = f"SIBI_Clean_{make_slug(key)}"

    run_mapreduce(
        input_key=extracted_key,
        output_key=target_output.rstrip("/"),
        job_name=job_name
    )

    logging.info(
        "SELESAI: %s -> s3://%s/%s",
        key, BUCKET, target_output
    )


# ==================================================
# MAIN POLLING LOOP
# ==================================================

def main():
    once = "--once" in sys.argv

    client = get_client()
    client.head_bucket(Bucket=BUCKET)

    logging.info("Pipeline otomatis aktif.")
    logging.info("Bucket: %s", BUCKET)
    logging.info("Mode: %s", "sekali jalan" if once else "monitoring")

    while True:
        try:
            pdfs = list_pdf_objects(client)

            for key in pdfs:
                try:
                    process_pdf(client, key)
                except Exception:
                    logging.exception(
                        "GAGAL memproses %s. "
                        "Pipeline akan mencoba lagi pada pemeriksaan berikutnya.",
                        key
                    )

        except Exception:
            logging.exception("Gagal memeriksa bucket MinIO.")

        if once:
            break

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
