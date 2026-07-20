-- Active: 1782769458259@@gateway01.ap-southeast-1.prod.aws.tidbcloud.com@4000@kurnia_rental@mysql
-- Active: 1781750281040@@gateway01.ap-southeast-1.prod.aws.tidbcloud.com@4000
CREATE DATABASE IF NOT EXISTS kurnia_rental;
USE kurnia_rental;

-- Tabel admin/pengguna sistem
CREATE TABLE IF NOT EXISTS admins (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(50) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel motor
CREATE TABLE IF NOT EXISTS motors (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    nama_motor      VARCHAR(100) NOT NULL,
    merk            VARCHAR(50) NOT NULL,
    tahun           INT,
    status          ENUM('tersedia','disewa','maintenance') DEFAULT 'tersedia',
    deskripsi       TEXT,
    gambar_url      VARCHAR(255),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Tabel pelanggan
CREATE TABLE IF NOT EXISTS customers (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    nama            VARCHAR(100) NOT NULL,
    no_hp           VARCHAR(20) NOT NULL,
    email           VARCHAR(100),
    tanggal_lahir   DATE,
    jenis_kelamin   VARCHAR(20),
    alamat          TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel booking/transaksi
CREATE TABLE IF NOT EXISTS bookings (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    motor_id        INT NOT NULL,
    customer_id     INT NOT NULL,
    jenis_sewa      ENUM('harian','paket') NOT NULL DEFAULT 'harian',
    tanggal_mulai   DATE NOT NULL,
    jam_mulai       TIME NULL,
    durasi_jam      INT NULL,
    paket_label     VARCHAR(20) NULL,
    tanggal_selesai DATE NOT NULL,
    total_hari      INT NOT NULL,
    total_harga     DECIMAL(12,2) NOT NULL,
    status          ENUM('pending','dikonfirmasi','selesai','dibatalkan') DEFAULT 'pending',
    catatan         TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (motor_id) REFERENCES motors(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- Sample data motor
INSERT INTO motors (nama_motor, merk, tahun, status, deskripsi) VALUES
('Honda Beat 2023', 'Honda', 2023, 'tersedia', 'Motor matic Honda Beat tahun 2023, irit dan nyaman untuk harian.'),
('Yamaha NMAX 2022', 'Yamaha', 2022, 'tersedia', 'Skutik premium NMAX, cocok untuk perjalanan jauh.'),
('Honda Vario 125 2023', 'Honda', 2023, 'tersedia', 'Vario 125 sporty dengan fitur keyless.'),
('Yamaha Mio M3 2021', 'Yamaha', 2021, 'tersedia', 'Mio M3 ringan dan lincALTER TABLE motors ADD CONSTRAINT uq_motors_plat_nomor UNIQUE (plat_nomor);
ah untuk dalam kota.'),
('Honda PCX 2022', 'Honda', 2022, 'disewa', 'PCX premium, nyaman dan stylish.');

USE kurnia_rental;

-- ================================================================
-- MIGRASI TAMBAHAN (jalankan setelah database awal sudah ada)
-- ================================================================
USE kurnia_rental;

-- Plat nomor motor
ALTER TABLE motors ADD COLUMN IF NOT EXISTS plat_nomor VARCHAR(20) NULL AFTER merk;
-- Pastikan tidak ada plat nomor yang sama persis (kosong/NULL boleh lebih dari satu)

-- Password untuk login customer via email (nullable = akun Google-only)
ALTER TABLE customers ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NULL;

-- Jam selesai (untuk sewa harian & per jam) + denda keterlambatan + waktu motor benar-benar dikembalikan
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS jam_selesai TIME NULL AFTER jam_mulai;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS denda DECIMAL(12,2) NOT NULL DEFAULT 0 AFTER total_harga;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS waktu_kembali TIMESTAMP NULL AFTER denda;

-- Tabel informasi sistem (dikelola admin, tampil di halaman Home customer)
CREATE TABLE IF NOT EXISTS site_info (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    isi         TEXT NOT NULL,
    urutan      INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ================================================================
-- MIGRASI: Plat nomor motor harus unik (tidak boleh sama)
-- ================================================================
USE kurnia_rental;

-- ================================================================
-- MIGRASI: Riwayat booking TETAP ADA walau customer hapus akunnya
-- (sebelumnya ON DELETE CASCADE = ikut terhapus, sekarang tidak lagi)
-- ================================================================
USE kurnia_rental;

-- Simpan juga nama & no HP customer langsung di baris booking (snapshot saat
-- booking dibuat), supaya riwayat tetap terbaca jelas walau baris customer-nya
-- sendiri sudah dihapus dari tabel customers.
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS customer_nama VARCHAR(100) NULL AFTER customer_id;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS customer_hp   VARCHAR(20)  NULL AFTER customer_nama;

-- Isi snapshot untuk data booking yang sudah ada sebelumnya, dari data customer saat ini
UPDATE bookings b
JOIN customers c ON b.customer_id = c.id
SET b.customer_nama = c.nama, b.customer_hp = c.no_hp
WHERE b.customer_nama IS NULL;

-- Ganti aturan hapus dari CASCADE (ikut terhapus) menjadi SET NULL (baris booking
-- tetap ada, cuma tautan ke customer_id-nya jadi kosong)
SET @fk_name = (
    SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'bookings'
    AND COLUMN_NAME = 'customer_id' AND REFERENCED_TABLE_NAME = 'customers'
    LIMIT 1
);
SET @drop_fk_sql = CONCAT('ALTER TABLE bookings DROP FOREIGN KEY ', @fk_name);
PREPARE stmt FROM @drop_fk_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE bookings MODIFY COLUMN customer_id INT NULL;
ALTER TABLE bookings ADD CONSTRAINT fk_bookings_customer
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL;

select * from motors: