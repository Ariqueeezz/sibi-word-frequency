# User Manual --- SIBI Word Frequency

Panduan ini menjelaskan cara menjalankan pipeline SIBI Word Frequency
mulai dari menyalakan layanan, mengunggah PDF ke MinIO, menjalankan
Hadoop MapReduce, hingga melihat hasil analisis pada dashboard
Streamlit.

## 1. Gambaran Umum

SIBI Word Frequency memproses buku digital berformat PDF untuk
menghitung frekuensi kata. Sistem menggunakan:

-   **MinIO** sebagai object storage.
-   **PyMuPDF** untuk mengekstrak teks dari PDF.
-   **Hadoop Streaming / MapReduce** untuk memproses dan menghitung
    frekuensi kata.
-   **Mapper dan reducer Python** untuk pembersihan teks dan agregasi
    frekuensi.
-   **Streamlit** untuk menampilkan hasil analisis melalui dashboard.

### Alur pemrosesan

1.  Pengguna mengunggah PDF ke root bucket `sibi-books`.
2.  Pipeline mendeteksi PDF di root bucket.
3.  Pipeline mengunduh PDF dan mengekstrak teksnya menggunakan PyMuPDF.
4.  Teks hasil ekstraksi diunggah ke `extracted/`.
5.  Pipeline menyalin skrip mapper, reducer, dan daftar stopword ke
    container NameNode.
6.  Hadoop Streaming menjalankan proses Word Count dan stopword removal.
7.  Hasil MapReduce disimpan di `output/`.
8.  Dashboard membaca file hasil dan menampilkan ringkasan serta
    visualisasi.

## 2. Prasyarat

Sebelum memulai, pastikan:

-   Docker dan Docker Compose tersedia di WSL.
-   Proyek berada di `~/sibi-word-frequency`.
-   File `minio.env` tersedia dan berisi konfigurasi MinIO yang
    diperlukan.
-   File `hadoop.env` tersedia untuk konfigurasi layanan Hadoop.
-   Virtual environment Python `.venv` dan dependensi proyek sudah
    disiapkan.
-   File mapper, reducer, dan stopword tersedia:
    -   `mapreduce/mapper_clean.py`
    -   `mapreduce/reducer.py`
    -   `mapreduce/stopwords_id.txt`

**Penting:** Jangan membagikan isi `minio.env` karena file tersebut
berisi kredensial. Perintah Compose pada panduan ini menggunakan
`--env-file minio.env` karena variabel MinIO diperlukan saat konfigurasi
container.

## 3. Menjalankan layanan

Buka terminal Ubuntu/WSL dan masuk ke direktori proyek:

``` bash
cd ~/sibi-word-frequency
```

Jalankan layanan Docker Compose:

``` bash
docker compose --env-file minio.env up -d
```

Periksa status container:

``` bash
docker compose --env-file minio.env ps
```

Pastikan layanan yang dibutuhkan berjalan. Untuk container Hadoop yang
memiliki health check, tunggu hingga statusnya `healthy`.

### Alamat layanan

  Layanan                   Alamat
  ------------------------- -------------------------
  MinIO Console             <http://localhost:9003>
  MinIO API                 `http://localhost:9002`
  Hadoop NameNode UI        <http://localhost:9870>
  YARN ResourceManager UI   <http://localhost:8088>
  NodeManager UI            <http://localhost:8042>
  Streamlit Dashboard       <http://localhost:8501>

MinIO Console digunakan untuk mengelola bucket dan objek melalui
browser. MinIO API digunakan oleh pipeline dan dashboard.

## 4. Mengunggah file PDF ke MinIO

1.  Buka <http://localhost:9003>.
2.  Login menggunakan kredensial MinIO yang tersimpan di `minio.env`.
3.  Buka bucket bernama `sibi-books`.
4.  Jika bucket belum tersedia, buat bucket dengan nama persis
    `sibi-books`.
5.  Unggah file PDF langsung ke root bucket, bukan ke subfolder.

Contoh struktur bucket:

``` text
sibi-books/
├── buku_pertama.pdf
├── buku_kedua.pdf
├── extracted/
│   ├── buku_pertama.txt
│   └── buku_kedua.txt
└── output/
    ├── wordcount_buku_pertama_clean_v1/
    └── wordcount_buku_kedua_clean_v1/
```

Struktur di atas merupakan ilustrasi. Folder `extracted/` dan `output/`
dibuat atau diisi oleh proses pipeline.

### Aturan input PDF

-   Pipeline hanya mencari objek yang nama kuncinya berakhiran `.pdf`
    dan tidak mengandung `/`. Dengan demikian, PDF harus berada langsung
    di root bucket.
-   Ekstensi `.pdf` diperiksa tanpa membedakan huruf besar/kecil.
-   Gunakan nama file yang jelas dan unik untuk setiap buku.
-   PDF harus berisi teks yang dapat diekstrak. PDF hasil scan yang
    hanya berupa gambar dapat gagal diproses karena pipeline saat ini
    tidak menjalankan OCR.

## 5. Menjalankan pipeline

### 5.1 Aktifkan virtual environment

Dari terminal WSL:

``` bash
cd ~/sibi-word-frequency
source .venv/bin/activate
```

### 5.2 Jalankan satu kali pemeriksaan

Untuk memeriksa bucket dan memproses PDF yang memenuhi kondisi pada satu
putaran, jalankan:

``` bash
python pipeline/auto_pipeline.py --once
```

Mode `--once` memeriksa bucket satu kali, memproses PDF yang ditemukan,
lalu berhenti setelah putaran tersebut selesai. Perintah ini cocok untuk
menjalankan pemrosesan secara manual.

### 5.3 Jalankan mode monitoring

Jika ingin pipeline terus memantau bucket, jalankan tanpa argumen
`--once`:

``` bash
python pipeline/auto_pipeline.py
```

Dalam mode ini, pipeline memeriksa bucket setiap 30 detik. Biarkan
terminal tetap berjalan selama monitoring diperlukan. Tekan `Ctrl+C`
untuk menghentikan proses secara manual.

### 5.4 Tahapan yang dilakukan pipeline

Untuk setiap PDF yang diproses, pipeline akan:

1.  Memeriksa apakah prefix output untuk buku tersebut sudah berisi
    objek.
2.  Mengunduh PDF dari MinIO ke `data/staging/`.
3.  Mengekstrak teks menggunakan PyMuPDF.
4.  Menyimpan teks lokal sementara dan mengunggahnya ke
    `extracted/<nama_file>.txt`.
5.  Menyalin `mapper_clean.py`, `reducer.py`, dan `stopwords_id.txt` ke
    `/tmp/` pada container `sibi-namenode`.
6.  Menjalankan Hadoop Streaming menggunakan input teks dari MinIO.
7.  Menyimpan output ke prefix `output/wordcount_<nama_buku>_clean_v1/`.

Pipeline membaca kredensial dari `minio.env`. Pastikan dependensi Python
tersedia dan perintah Docker dapat dijalankan dari terminal yang
menjalankan pipeline.

### 5.5 Membaca log pipeline

Log ditampilkan di terminal. Pesan yang berguna antara lain:

-   `Mulai memproses PDF` --- pipeline mulai memproses file.
-   `Ekstraksi berhasil` --- teks berhasil diekstrak; log juga
    menampilkan jumlah halaman dan karakter.
-   `Teks tersimpan` --- teks hasil ekstraksi telah diunggah ke MinIO.
-   `Menjalankan Hadoop MapReduce` --- job MapReduce mulai dijalankan.
-   `SELESAI` --- perintah MapReduce selesai tanpa memunculkan error
    pada proses tersebut.
-   `Lewati ... output sudah ada` --- file dilewati karena prefix output
    sudah berisi setidaknya satu objek.
-   `GAGAL memproses` --- terjadi error pada file; detail error dicatat
    pada log.

Perlu diperhatikan: pesan `SELESAI` menunjukkan perintah Hadoop selesai
tanpa error yang terdeteksi oleh subprocess, tetapi pemeriksaan hasil di
MinIO dan dashboard tetap perlu dilakukan.

## 6. Cara kerja Mapper dan Reducer

### 6.1 Mapper: pembersihan dan pemfilteran kata

File `mapreduce/mapper_clean.py`:

-   Mengubah teks menjadi huruf kecil.
-   Mengambil rangkaian huruf Unicode.
-   Mengabaikan angka, tanda baca, dan garis bawah sebagai token.
-   Mengabaikan kata yang panjangnya satu karakter.
-   Menghapus kata yang terdapat dalam `stopwords_id.txt`.
-   Menghasilkan pasangan `kata<TAB>1` untuk setiap kata yang lolos
    filter.

### 6.2 Reducer: menghitung frekuensi

File `mapreduce/reducer.py` menerima pasangan kata dan hitungan,
kemudian menjumlahkan hitungan untuk setiap kata yang sama.

Hasil MapReduce berupa baris teks dengan format:

``` text
kata<TAB>frekuensi
```

Contoh ilustratif:

``` text
analisis    2
buku        1
data        3
```

Kata dan frekuensi pada contoh tersebut hanya ilustrasi; hasil aktual
bergantung pada isi PDF dan daftar stopword. Hadoop biasanya menyimpan
hasil partisi reducer dalam file seperti `part-00000`.

## 7. Memeriksa hasil di MinIO

Setelah pipeline selesai:

1.  Buka MinIO Console di <http://localhost:9003>.
2.  Buka bucket `sibi-books`.
3.  Periksa folder `extracted/` dan pastikan file TXT hasil ekstraksi
    tersedia.
4.  Buka `output/`.
5.  Cari folder dengan pola `wordcount_<nama_buku>_clean_v1/`.
6.  Pastikan folder hasil berisi file `part-*`, misalnya `part-00000`.

Nama output dibentuk dari nama file PDF. Pipeline menormalisasi nama
menjadi slug, mengganti rangkaian karakter selain huruf dan angka
menjadi garis bawah. Ada aturan khusus: nama yang diawali
`dasar_teknika_kapal_penangkap_ikan` menggunakan slug `dasar_teknika`.

## 8. Menjalankan dashboard

Buka terminal WSL kedua agar terminal pipeline tetap dapat dipantau.

``` bash
cd ~/sibi-word-frequency
source .venv/bin/activate
streamlit run dashboard/app.py
```

Buka <http://localhost:8501> di browser.

Dashboard **Analisis Frekuensi Kata Buku Digital SIBI** mengambil daftar
folder dari `output/` di bucket `sibi-books`, membaca file yang namanya
diawali `part-`, lalu membentuk tabel kata dan frekuensi.

### Informasi di dashboard

Dashboard menghitung atau menampilkan metrik berdasarkan data hasil
MapReduce, termasuk:

-   Total kemunculan kata.
-   Jumlah kata unik.
-   Kata dengan frekuensi tertinggi.
-   Frekuensi kata untuk hasil analisis yang dipilih.
-   Visualisasi yang tersedia pada halaman dashboard.

Gunakan dropdown **Pilih hasil analisis** untuk memilih folder output.
Dashboard memprioritaskan folder yang namanya mengandung `_clean_v`
sebagai pilihan default jika tersedia.

Tombol **Muat ulang data** membersihkan cache terkait dan memuat ulang
tampilan. Data hasil memiliki cache dengan waktu kedaluwarsa 60 detik,
sehingga perubahan di MinIO mungkin tidak langsung terlihat sebelum
cache diperbarui.

Jika baru satu buku yang diproses, fitur perbandingan yang memerlukan
lebih dari satu buku mungkin belum tersedia atau menampilkan peringatan.

## 9. Checklist verifikasi

Gunakan checklist ini setiap selesai memproses PDF:

-   [ ] Container Hadoop dan MinIO berjalan.
-   [ ] PDF diunggah langsung ke root bucket `sibi-books`.
-   [ ] Pipeline berjalan tanpa error untuk PDF yang diuji.
-   [ ] File teks tersedia di `extracted/`.
-   [ ] Folder output buku tersedia di `output/`.
-   [ ] Folder output berisi file `part-*`.
-   [ ] Dashboard dapat membaca dan menampilkan hasil analisis.

Jangan menyatakan pemrosesan berhasil hanya berdasarkan keberadaan
folder output. Periksa juga file `part-*` dan hasil yang ditampilkan
dashboard.

## 10. Troubleshooting

### 10.1 Docker Compose meminta variabel MinIO

Gunakan perintah dengan file environment:

``` bash
docker compose --env-file minio.env up -d
```

Pastikan `minio.env` ada dan memuat variabel yang diperlukan. Jangan
menempelkan nilai kredensial ke dokumentasi atau percakapan.

### 10.2 Pipeline tidak menemukan PDF

-   Pastikan bucket bernama `sibi-books`.
-   Pastikan file berada di root bucket, bukan di subfolder.
-   Pastikan nama file berakhiran `.pdf`.
-   Pastikan pipeline terhubung ke endpoint MinIO yang benar.

### 10.3 PDF gagal diekstrak

Pastikan PDF dapat dibuka dan berisi teks yang bisa dipilih atau
diekstrak. Jika PDF hanya berupa gambar hasil scan, OCR mungkin
diperlukan; OCR tidak termasuk dalam kode pipeline yang dijelaskan di
panduan ini.

### 10.4 Hadoop MapReduce gagal

Periksa log terminal untuk detail error. Pastikan container
`sibi-namenode` berjalan dan file berikut tersedia di proyek:

-   `mapreduce/mapper_clean.py`
-   `mapreduce/reducer.py`
-   `mapreduce/stopwords_id.txt`

Periksa juga konfigurasi akses S3A Hadoop ke MinIO serta status layanan
Hadoop.

### 10.5 Dashboard tidak menemukan hasil

-   Pastikan pipeline selesai tanpa error.
-   Periksa apakah folder output berisi file `part-*`.
-   Pastikan dashboard menggunakan bucket `sibi-books` dan endpoint
    MinIO yang benar.
-   Tekan tombol **Muat ulang data** pada sidebar.

### 10.6 Pipeline melewati PDF yang ingin diproses ulang

Pipeline melewati buku jika prefix output yang dihitung untuk buku itu
sudah memiliki setidaknya satu objek. Pengecekan ini tidak memastikan
bahwa seluruh hasil lengkap.

Jika perlu memproses ulang, periksa terlebih dahulu isi prefix output
dan log job. Jangan menghapus objek output secara sembarangan karena
objek tersebut mungkin merupakan hasil analisis yang masih dibutuhkan.
Prosedur penghapusan atau penggantian output sebaiknya mengikuti
kebijakan pengelolaan data proyek.

### 10.7 Kredensial MinIO tidak ditemukan atau koneksi gagal

-   Pastikan `minio.env` tersedia di root proyek.
-   Pastikan nama variabel yang digunakan sesuai dengan konfigurasi
    proyek.
-   Pastikan container MinIO berjalan.
-   Jangan menuliskan nilai secret pada log manual atau membagikannya
    kepada pihak lain.

## 11. Menghentikan sistem

Untuk menghentikan layanan Docker Compose:

``` bash
cd ~/sibi-word-frequency
docker compose --env-file minio.env down
```

Perintah ini menghentikan dan menghapus container Compose, tetapi tidak
menghapus named volume selama opsi `-v` tidak digunakan. Data yang
disimpan dalam volume tetap ada.

Jika pipeline dijalankan dalam mode monitoring, hentikan proses tersebut
secara terpisah dengan menekan `Ctrl+C` pada terminal pipeline. Hentikan
Streamlit dengan `Ctrl+C` pada terminal dashboard.

## 12. Catatan operasional

1.  **Output yang sudah ada dapat menyebabkan file dilewati.** Pipeline
    hanya memeriksa apakah ada objek dengan prefix output yang
    ditentukan.
2.  **Output parsial perlu ditinjau.** Keberadaan satu objek belum tentu
    berarti job berhasil sepenuhnya.
3.  **PDF hasil scan tidak otomatis diproses dengan OCR.**
4.  **Dashboard membaca hasil dari MinIO, bukan menjalankan MapReduce
    sendiri.** Jalankan pipeline terlebih dahulu sebelum membuka hasil
    analisis.
5.  **Lindungi kredensial.** Jangan memasukkan nilai dari `minio.env` ke
    dokumentasi yang dibagikan secara publik.

------------------------------------------------------------------------

**Akhir panduan.**
