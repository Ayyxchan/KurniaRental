# Kurnia Rental — Sistem Informasi Sewa Motor

Aplikasi web sewa motor dengan dua sisi:
- **Admin**: Login, kelola data motor (CRUD), konfirmasi booking, dashboard statistik
- **Customer**: Lihat daftar motor, pesan online, cek status booking — selalu real-time dari data admin

**Stack**: Python + Flask (Backend), HTML/CSS/JS Vanilla (Frontend), MySQL (Database)

---

## Struktur Folder

```
KurniaRental/
├── app.py                    # Entry point Flask
├── config.py                 # Konfigurasi (DB, secret key)
├── model.py                  # Database connection pool
├── create_admin.py           # Script buat akun admin
├── database.sql              # Skema + sample data
├── requirements.txt
├── .env.example
├── Backend/
│   ├── admin/
│   │   ├── login.py          # Login/logout/auth check
│   │   ├── motors.py         # CRUD motor (admin)
│   │   └── bookings.py       # Kelola booking + dashboard stats
│   └── customer/
│       └── customer.py       # API publik (list motor, buat booking, cek booking)
└── Frontend/
    ├── admin/
    │   ├── css/style.css
    │   ├── login.html
    │   ├── dashboard.html
    │   ├── motors.html
    │   └── bookings.html
    └── customer/
        ├── css/style.css
        ├── js/script.js
        └── index.html
```

---

## Setup & Menjalankan

### 1. Siapkan MySQL

Pastikan MySQL berjalan. Buka MySQL client dan jalankan:

```sql
-- Bisa via phpMyAdmin, MySQL Workbench, atau terminal:
mysql -u root -p < database.sql
```

### 2. Konfigurasi `.env`

```bash
cp .env.example .env
```

Edit `.env` sesuai konfigurasi MySQL kamu:

```env
FLASK_DEBUG=True
SECRET_KEY=kurnia-rental-secret-2024

DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password_mysql_kamu
DB_NAME=kurnia_rental
```

### 3. Install Dependencies

```bash
# (Disarankan) Buat virtual environment dulu
python -m venv venv
venv\Scripts\activate     # Windows
# atau
source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
```

### 4. Buat Akun Admin

```bash
python create_admin.py
# Masukkan username dan password admin
```

### 5. Jalankan Aplikasi

```bash
python app.py
```

Aplikasi berjalan di **http://localhost:5000**

---

## Akses Aplikasi

| URL | Keterangan |
|-----|------------|
| `http://localhost:5000/` | Halaman Customer |
| `http://localhost:5000/admin` | Login Admin |
| `http://localhost:5000/admin/dashboard.html` | Dashboard Admin |
| `http://localhost:5000/admin/motors.html` | Kelola Motor |
| `http://localhost:5000/admin/bookings.html` | Kelola Booking |

---

## API Endpoints

### Public (Customer)
| Method | Endpoint | Keterangan |
|--------|----------|------------|
| GET | `/api/motors` | Daftar semua motor |
| GET | `/api/motors/<id>` | Detail motor |
| POST | `/api/booking` | Buat booking baru |
| GET | `/api/booking/cek?no_hp=...` | Cek status booking |

### Admin (perlu login)
| Method | Endpoint | Keterangan |
|--------|----------|------------|
| POST | `/api/admin/login` | Login |
| POST | `/api/admin/logout` | Logout |
| GET | `/api/admin/auth/check` | Cek status login |
| GET | `/api/admin/dashboard/stats` | Statistik dashboard |
| GET/POST | `/api/admin/motors` | List/tambah motor |
| PUT/DELETE | `/api/admin/motors/<id>` | Edit/hapus motor |
| GET | `/api/admin/bookings` | Semua booking |
| PATCH | `/api/admin/bookings/<id>/status` | Update status booking |

---

## Alur Sistem

1. **Admin** login → tambah/edit motor → motor langsung terlihat di halaman customer
2. **Customer** buka halaman, pilih motor, isi form booking → status "pending"
3. **Admin** lihat booking masuk → klik "Konfirmasi" → motor otomatis jadi "Disewa"
4. Saat sewa selesai → Admin klik "Selesai" → motor kembali "Tersedia"
5. Halaman customer auto-refresh setiap 30 detik (status motor selalu up-to-date)
