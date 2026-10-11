# Tuntas - IT Ticketing & Service Desk Management System

<p align="center">
  <img src="tickets/static/images/logo-tuntas.png" alt="Tuntas Logo" width="120" />
</p>

<p align="center">
  <strong>Sistem Manajemen Tiket Bantuan & Service Desk IT Internal Modern berbasis Django</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python Version" />
  <img src="https://img.shields.io/badge/Django-6.1-green.svg" alt="Django Version" />
  <img src="https://img.shields.io/badge/License-MIT-purple.svg" alt="License" />
</p>

---

## Tentang Proyek

**Tuntas** adalah platform helpdesk & service desk internal yang dirancang untuk mempercepat alur penanganan masalah IT di perusahaan. Dilengkapi sistem *Role-Based Access Control* (RBAC), pelacakan SLA, antrean penugasan teknisi otomatis/manual, dan pelaporan evaluasi kinerja teknisi.

---

## Fitur Utama

- **Multi-Role Access Control (RBAC)**:
  - **Administrator**: Kontrol penuh master pengguna, kategori tiket, pengaturan sistem, switch role instan, dan unduh laporan kinerja.
  - **IT Lead / Supervisor**: Monitoring antrean tiket keseluruhan, alokasi penugasan teknisi (*Assign to*), dan pantauan SLA tim.
  - **Staff IT / Teknisi**: Menerima penugasan tugas dari Lead, dashboard antrean personal **"Tugas Saya"**, update progres fiksasi tiket, catatan internal IT, dan input solusi perbaikan.
  - **Karyawan / Requester**: Fokus pelaporan aduan kendala (*Fokus Aduan*), pelacakan progres tiket sendiri, konfirmasi selesai, re-open tiket, dan penilaian kepuasan (*Rating & Review*).
- **Penilaian Kepuasan Pelapor (CSAT 1-5 Bintang)**: Pelapor dapat memberikan rating bintang serta ulasan masukan saat tiket selesai ditangani.
- **Otomatisasi SLA Due Date & Indikator Keterlambatan**: Batas waktu penyelesaian dihitung otomatis berdasarkan prioritas (Urgent: 4j, High: 12j, Medium: 24j, Low: 48j) dengan visual peringatan keterlambatan (*Over SLA*).
- **Siklus Re-Open & Konfirmasi Selesai**: Karyawan memverifikasi hasil penanganan; tiket dapat dibuka kembali jika kendala belum tuntas, atau ditutup permanen.
- **Catatan Solusi Resmi Teknisi (*Resolution Note*)**: Dokumentasi tindakan perbaikan teknis yang dilakukan tim IT tersimpan rapi pada tiket.
- **Switch Role Instan (Admin Sandbox)**: Kemudahan berpindah sudut pandang antar-role langsung dari navbar tanpa logout-login berulang.
- **Laporan & Export Penilaian Komprehensif**: Unduh rekap penilaian performa tiket, kepatuhan SLA, durasi fiksasi, dan skor CSAT dalam format CSV/Excel.
- **Desain UI Modern**: Tampilan bersih, responsif, dan interaktif dengan mode gelap/terang didukung CSS modern (*ReactBits styled components*).

---

## Tech Stack

- **Backend**: Python, Django 6.1
- **Database**: SQLite (Development) / PostgreSQL (Production ready)
- **Frontend**: Django Templates, Vanilla CSS & ReactBits modern styling
- **Ekspor Data**: Python CSV Stream Engine

---

## Panduan Instalasi & Menjalankan Lokal

### 1. Clone Repositori
```bash
git clone https://github.com/narendrasatyaa/tuntas-ticket.git
cd tuntas-ticket
```

### 2. Siapkan Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate    # Di Linux / macOS
# venv\Scripts\activate     # Di Windows
```

### 3. Install Dependensi
```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Environment (Opsional)
Salin berkas contoh konfigurasi lingkungan:
```bash
cp .env.example .env
```

### 5. Jalankan Migrasi Database
```bash
python3 manage.py migrate
```

### 6. Isi Data Awal / Seeding Akun Uji Coba
Sistem telah dilengkapi skrip data awal berisi kategori dan akun per role:
```bash
python3 seed_data.py
```

### 7. Jalankan Server Lokal
```bash
python3 manage.py runserver
```
Buka browser dan akses [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## Akun Demo (Default Seed)

Setelah menjalankan `python3 seed_data.py`, Anda dapat login menggunakan akun berikut:

| Role | Username | Password | Deskripsi Tugas |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin` | `password123` | Akses penuh master data & export |
| **IT Supervisor** | `lead` | `password123` | Monitor antrean & assign teknisi |
| **Staff IT / Teknisi**| `teknisi` | `password123` | Eksekusi tiket di "Tugas Saya" |
| **Karyawan / User** | `budi` | `password123` | Buat tiket & berikan ulasan |

---

## Struktur Direktori

```text
├── config/                 # Konfigurasi project Django (settings, urls, wsgi)
├── tickets/                # Aplikasi inti manajemen tiket
│   ├── migrations/         # File migrasi skema database
│   ├── static/             # Static assets (CSS, images, icons)
│   ├── templates/          # Template HTML UI multi-role
│   ├── forms.py            # Form validation & input handler
│   ├── models.py           # Model database Ticket, Category, UserProfile
│   ├── views.py            # Logika alur tiket, antrean, dan export laporan
│   └── urls.py             # Rute URL modul tiket
├── seed_data.py            # Skrip seeder data awal untuk pengujian
├── manage.py               # Django CLI utility
├── requirements.txt        # Daftar dependensi Python
└── README.md               # Dokumentasi proyek
```

---

## Lisensi

Proyek ini dirilis di bawah lisensi [MIT License](LICENSE).
