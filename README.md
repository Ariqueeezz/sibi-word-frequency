# SIBI Word Frequency

Project Big Data untuk menghitung frekuensi kemunculan kata dari dokumen PDF menggunakan Hadoop MapReduce, menyimpan data dan hasil pemrosesan pada MinIO, serta menampilkan hasil analisis melalui dashboard Streamlit.

## 1. Tujuan Project

Project ini bertujuan membangun pipeline pemrosesan teks dokumen PDF yang mencakup:

- Pengambilan dan ekstraksi teks dari dokumen PDF.
- Penyimpanan data teks menggunakan MinIO dengan kompatibilitas S3.
- Pemrosesan terdistribusi menggunakan Hadoop Streaming dan MapReduce.
- Pembersihan teks dan penghapusan stopwords bahasa Indonesia.
- Visualisasi hasil analisis melalui dashboard Streamlit.

## 2. Teknologi

| Teknologi | Fungsi |
|---|---|
| Docker Compose | Menjalankan layanan dalam container |
| Hadoop HDFS | Penyimpanan terdistribusi Hadoop |
| Hadoop MapReduce | Pemrosesan data secara batch |
| Hadoop Streaming | Menjalankan mapper dan reducer Python |
| MinIO | Penyimpanan objek dengan API kompatibel S3 |
| Python | Implementasi pipeline dan logika pemrosesan |
| PyMuPDF | Ekstraksi teks PDF |
| Boto3 | Integrasi Python dengan MinIO |
| Streamlit | Dashboard interaktif |
| Pandas | Pengolahan hasil untuk dashboard |
| Matplotlib | Visualisasi data |
| WordCloud | Visualisasi frekuensi kata |

## 3. Struktur Project

```text
sibi-word-frequency/
├── dashboard/
│   └── app.py
├── data/
│   ├── source/
│   ├── staging/
│   ├── extracted/
│   ├── metadata/
│   └── raw/
├── docs/
│   └── experiments/
├── mapreduce/
│   ├── mapper.py
│   ├── mapper_clean.py
│   ├── mapper_nfkc_test.py
│   ├── reducer.py
│   └── stopwords_id.txt
├── pipeline/
│   └── auto_pipeline.py
├── .gitignore
├── core-site-s3a.xml
├── docker-compose.yml
├── Dockerfile.nodemanager
├── hadoop.env
├── minio.env
└── requirements.txt
```

Catatan: isi folder `data/` dapat berubah selama pipeline berjalan. File eksperimen disimpan terpisah dari pipeline utama.

## 4. Prasyarat

- Docker Engine atau Docker Desktop dengan dukungan Docker Compose.
- Python 3 dan virtual environment.
- Dokumen PDF sebagai input.
- File konfigurasi layanan yang sesuai dengan environment lokal.

## 5. Konfigurasi

Konfigurasi layanan Docker berada pada `docker-compose.yml`, `hadoop.env`, dan `core-site-s3a.xml`.

Konfigurasi kredensial MinIO disimpan pada `minio.env`. File tersebut bersifat lokal dan tidak boleh dipublikasikan ke repositori.

Jangan membagikan password, access key, secret key, atau kredensial lain dalam dokumentasi maupun tangkapan layar.

## 6. Instalasi Python

Aktifkan virtual environment:

```bash
source .venv/bin/activate
```

Pasang dependensi:

```bash
pip install -r requirements.txt
```

## 7. Menjalankan Layanan

Dari direktori project, jalankan:

```bash
docker compose up -d
```

Periksa status container:

```bash
docker compose ps
```

Lihat log jika ada layanan yang bermasalah:

```bash
docker compose logs --tail=100
```

## 8. Pipeline Pemrosesan

Pipeline utama berada pada `pipeline/auto_pipeline.py`.

Secara umum, prosesnya meliputi:

1. Memindai dokumen PDF yang tersedia pada penyimpanan MinIO.
2. Mengunduh dokumen yang akan diproses ke direktori staging.
3. Mengekstrak teks dari PDF.
4. Mengunggah teks hasil ekstraksi ke MinIO.
5. Menyiapkan skrip mapper, reducer, dan daftar stopwords untuk Hadoop Streaming.
6. Menjalankan pekerjaan Word Frequency menggunakan Hadoop.
7. Menyimpan hasil pemrosesan ke MinIO.

Pipeline menyediakan opsi pemindaian satu kali (`--once`) dan pemantauan berkala. Periksa argumen yang tersedia di kode sebelum menjalankannya.

## 9. MapReduce

Implementasi pemrosesan berada pada direktori `mapreduce/`.

- `mapper_clean.py`: membersihkan teks dan mempersiapkan kata untuk dihitung.
- `reducer.py`: menggabungkan hasil berdasarkan kata dan menghitung frekuensinya.
- `stopwords_id.txt`: daftar stopwords bahasa Indonesia.

Hasil pemrosesan disimpan di MinIO. Nama direktori output mengikuti konfigurasi pipeline dan identitas dokumen yang diproses.

## 10. Dashboard

Dashboard dibuat menggunakan Streamlit dan berada pada `dashboard/app.py`.

Jalankan dashboard dengan:

```bash
streamlit run dashboard/app.py
```

Alamat lokal default Streamlit biasanya:

http://localhost:8501

Dashboard membutuhkan akses ke hasil pemrosesan yang tersedia di MinIO.

## 11. Pengujian

Pengujian dasar meliputi:

- Memastikan seluruh container berjalan.
- Memastikan bucket dan akses MinIO tersedia.
- Memastikan PDF dapat diekstrak menjadi teks.
- Memastikan pekerjaan Hadoop Streaming selesai tanpa error.
- Memastikan hasil Word Frequency tersimpan di MinIO.
- Memastikan dashboard dapat membaca dan menampilkan hasil.

Simpan bukti pengujian aktual, seperti status container, log pipeline, hasil MapReduce, dan tampilan dashboard, pada dokumentasi project.

## 12. Keamanan dan Pengelolaan File

- Jangan memasukkan kredensial ke Git.
- Jangan menyimpan file sementara atau hasil generated ke repositori tanpa kebutuhan yang jelas.
- Gunakan `.gitignore` untuk mengecualikan file lokal dan rahasia.
- Pertahankan dokumen sumber yang diperlukan untuk pengujian dan dokumentasi.

## 13. Status Dokumentasi

README ini merupakan panduan awal. Detail arsitektur, konfigurasi layanan, prosedur pengujian, dan bukti hasil implementasi akan didokumentasikan secara terpisah.
