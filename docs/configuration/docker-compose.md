# Dokumentasi Konfigurasi Docker Compose

## 1. Tujuan

Dokumentasi ini menjelaskan konfigurasi Docker Compose untuk menjalankan layanan SIBI Word Frequency. Docker Compose digunakan untuk mengelola container, jaringan, port, environment, batas memori, dan persistensi data.

## 2. Daftar Layanan

| Layanan | Container | Image | Batas Memori |
|---|---|---|---|
| NameNode | `sibi-namenode` | `bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8` | 768 MB |
| DataNode | `sibi-datanode` | `bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8` | 768 MB |
| ResourceManager | `sibi-resourcemanager` | `bde2020/hadoop-resourcemanager:2.0.0-hadoop3.2.1-java8` | 768 MB |
| NodeManager | `sibi-nodemanager` | `sibi-nodemanager-python:latest` | 1200 MB |
| MinIO | `sibi-minio` | `minio-lokal:latest` | 512 MB |

NodeManager menggunakan image kustom yang dibangun dari `Dockerfile.nodemanager`. Image tersebut disiapkan untuk mendukung kebutuhan Python pada lingkungan pemrosesan.

MinIO menggunakan image lokal `minio-lokal:latest`.

## 3. Pemetaan Port

| Layanan | Port Host | Port Container | Fungsi |
|---|---:|---:|---|
| NameNode | 9870 | 9870 | Web UI NameNode |
| NameNode | 9000 | 9000 | Port layanan NameNode |
| DataNode | 9864 | 9864 | Layanan dan Web UI DataNode |
| ResourceManager | 8088 | 8088 | Web UI YARN |
| NodeManager | 8042 | 8042 | Web UI NodeManager |
| MinIO API | 9002 | 9000 | Akses object storage |
| MinIO Console | 9003 | 9001 | Antarmuka pengelolaan MinIO |

### URL Akses

- NameNode UI: `http://localhost:9870`
- YARN ResourceManager UI: `http://localhost:8088`
- NodeManager UI: `http://localhost:8042`
- MinIO API: `http://localhost:9002`
- MinIO Console: `http://localhost:9003`

Port yang dipublikasikan dapat diakses melalui host sesuai konfigurasi jaringan dan firewall.

## 4. Konfigurasi Environment

Layanan Hadoop menggunakan `hadoop.env` untuk memuat konfigurasi Hadoop.

Layanan MinIO menggunakan `minio.env` melalui bagian `env_file`.

Konfigurasi kredensial S3A diteruskan ke layanan Hadoop melalui environment variable berikut:

```text
CORE_CONF_fs_s3a_access_key
CORE_CONF_fs_s3a_secret_key
```

Nilainya mengacu pada environment variable Compose:

```text
MINIO_ROOT_USER
MINIO_ROOT_PASSWORD
```

**Catatan:** `env_file` memasukkan environment variable ke dalam container. File tersebut tidak otomatis menyediakan variable untuk interpolasi `${...}` pada saat Docker Compose membaca konfigurasi. Pastikan variable yang diperlukan tersedia di environment shell atau file `.env` yang dibaca Compose.

Jangan menyimpan kredensial asli di dokumentasi atau repository Git.

## 5. Jaringan Docker

Semua layanan menggunakan jaringan bridge:

```yaml
networks:
  sibi-network:
    driver: bridge
```

Karena berada dalam jaringan yang sama, layanan Hadoop mengakses MinIO menggunakan nama service dan port internal:

```text
http://minio:9000
```

Sementara itu, aplikasi yang berjalan di host menggunakan:

```text
http://localhost:9002
```

## 6. Persistensi Data

Konfigurasi mendefinisikan tiga named volume:

```yaml
volumes:
  namenode_data:
  datanode_data:
  minio_data:
```

Pemetaan volume:

| Volume | Lokasi Container | Kegunaan |
|---|---|---|
| `namenode_data` | `/hadoop/dfs/name` | Persistensi metadata NameNode |
| `datanode_data` | `/hadoop/dfs/data` | Persistensi data HDFS pada DataNode |
| `minio_data` | `/data` | Persistensi objek MinIO |

Hindari menjalankan `docker compose down -v` jika ingin mempertahankan data pada named volume.

## 7. Dependensi Layanan

Konfigurasi `depends_on` menentukan urutan dependensi antarlayanan pada saat Compose memulai container.

NodeManager bergantung pada NameNode, DataNode, dan ResourceManager. ResourceManager juga memiliki dependensi terhadap NameNode dan DataNode.

Perlu diperhatikan bahwa `depends_on` biasa tidak selalu menjamin sebuah layanan telah siap sepenuhnya menerima koneksi. Pemeriksaan kesehatan dan kesiapan layanan perlu diverifikasi secara terpisah.

## 8. Batas Memori

Batas memori container ditetapkan agar penggunaan sumber daya tetap terkendali pada lingkungan komputasi lokal.

| Layanan | Batas |
|---|---:|
| NameNode | 768 MB |
| DataNode | 768 MB |
| ResourceManager | 768 MB |
| NodeManager | 1200 MB |
| MinIO | 512 MB |

Batas tersebut merupakan konfigurasi maksimum container, bukan jaminan bahwa seluruh memori akan digunakan.

## 9. Menjalankan Sistem

Jalankan perintah berikut dari direktori root proyek yang berisi `docker-compose.yml`.

### Memvalidasi konfigurasi

```bash
docker compose config
```

Pastikan konfigurasi berhasil dirender tanpa error.

### Menjalankan layanan

```bash
docker compose up -d
```

### Memeriksa status container

```bash
docker compose ps
```

### Melihat log

```bash
docker compose logs --tail=100
```

Untuk melihat log layanan tertentu:

```bash
docker compose logs --tail=100 namenode
docker compose logs --tail=100 datanode
docker compose logs --tail=100 resourcemanager
docker compose logs --tail=100 nodemanager
docker compose logs --tail=100 minio
```

### Menghentikan layanan

```bash
docker compose down
```

Perintah ini menghentikan dan menghapus container serta jaringan yang dibuat Compose, tetapi tidak menghapus named volume secara default.

## 10. Kesimpulan

Docker Compose mengintegrasikan komponen Hadoop dan MinIO dalam jaringan Docker yang sama. Pemetaan port memungkinkan akses antarmuka pengelolaan dari host, sedangkan named volume mendukung persistensi data. Konfigurasi environment, dependensi layanan, dan batas memori membantu menjalankan sistem secara konsisten pada lingkungan lokal.
