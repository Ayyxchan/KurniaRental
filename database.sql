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
    customer_id     INT NULL,
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
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);

-- Sample data motor
INSERT INTO motors (nama_motor, merk, tahun, status, deskripsi) VALUES
('Honda Beat 2023', 'Honda', 2023, 'tersedia', 'Motor matic Honda Beat tahun 2023, irit dan nyaman untuk harian.'),
('Yamaha NMAX 2022', 'Yamaha', 2022, 'tersedia', 'Skutik premium NMAX, cocok untuk perjalanan jauh.'),
('Honda Vario 125 2023', 'Honda', 2023, 'tersedia', 'Vario 125 sporty dengan fitur keyless.'),
('Yamaha Mio M3 2021', 'Yamaha', 2021, 'tersedia', 'Mio M3 ringan dan lincah untuk dalam kota.'),
('Honda PCX 2022', 'Honda', 2022, 'disewa', 'PCX premium, nyaman dan stylish.');

USE kurnia_rental;


USE kurnia_rental;

-- Plat nomor motor
ALTER TABLE motors ADD COLUMN IF NOT EXISTS plat_nomor VARCHAR(20) NULL AFTER merk;

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


ALTER TABLE bookings ADD COLUMN IF NOT EXISTS nama_pelanggan VARCHAR(100) NULL AFTER customer_id;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS no_hp_pelanggan VARCHAR(20) NULL AFTER nama_pelanggan;

UPDATE bookings b
JOIN customers c ON b.customer_id = c.id
SET b.nama_pelanggan  = c.nama,
    b.no_hp_pelanggan = c.no_hp
WHERE b.nama_pelanggan IS NULL;

SELECT id, customer_id, nama_pelanggan, no_hp_pelanggan FROM bookings LIMIT 10;


SELECT plat_nomor, COUNT(*) AS jumlah
FROM motors
WHERE plat_nomor IS NOT NULL AND plat_nomor <> ''
GROUP BY plat_nomor
HAVING COUNT(*) > 1;


UPDATE motors SET plat_nomor = NULL WHERE plat_nomor = '';

ALTER TABLE motors ADD CONSTRAINT uq_motors_plat_nomor UNIQUE (plat_nomor);


SELECT CONSTRAINT_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'kurnia_rental'
  AND TABLE_NAME = 'bookings'
  AND COLUMN_NAME = 'customer_id'
  AND REFERENCED_TABLE_NAME = 'customers';

ALTER TABLE bookings DROP FOREIGN KEY fk_bookings_customer;

ALTER TABLE bookings MODIFY customer_id INT NULL;

ALTER TABLE bookings ADD CONSTRAINT fk_bookings_customer
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL;
