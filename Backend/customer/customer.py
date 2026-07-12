from flask import Blueprint, request, jsonify
from model import Database
from config import Config
from datetime import datetime, timedelta, time as dtime
from werkzeug.security import generate_password_hash, check_password_hash
import json
import math
import time
import urllib.request
import urllib.error
import urllib.parse

customer_bp = Blueprint('customer', __name__)
db = Database()
_customer_columns_cache = None

# ── Rate limiter sederhana untuk cegah brute-force login customer ──
_login_attempts = {}
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300  # 5 menit


def _rate_limited(key):
    now = time.time()
    attempts = [t for t in _login_attempts.get(key, []) if now - t < WINDOW_SECONDS]
    _login_attempts[key] = attempts
    return len(attempts) >= MAX_ATTEMPTS


def _record_attempt(key):
    _login_attempts.setdefault(key, []).append(time.time())

TARIF_HARIAN = 50000
DENDA_PER_JAM = 5000  # denda keterlambatan pengembalian motor, per jam kelebihan

# Harga sewa per jam: titik "anchor" (harga paket khusus/diskon di jam tersebut),
# dan di ANTARA anchor naik Rp5.000 setiap jam dari anchor terdekat di bawahnya.
# Jadi: 1 jam=10rb, 2 jam=15rb, 3 jam=20rb, 4 jam=25rb, 5 jam=30rb,
#       6 jam=25rb (anchor/harga paket sendiri, bukan hasil naik 5rb),
#       7 jam=30rb, ... 11 jam=50rb, 12 jam=35rb (anchor lagi), dst.
JAM_ANCHORS = [
    (1,  10000),
    (6,  25000),
    (12, 35000),
    (24, 50000),
    (72, 140000),
]
KENAIKAN_PER_JAM = 5000


def compute_daily_price(total_hari):
    """Tarif harian: 1 hari 50rb, 2 hari 100rb, 3 hari 140rb (paket diskon).
    Lebih dari 3 hari kembali ke tarif normal 50rb/hari (4 hari = 200rb, dst)."""
    tiers = {1: 50000, 2: 100000, 3: 140000}
    if total_hari in tiers:
        return tiers[total_hari]
    return total_hari * TARIF_HARIAN


def compute_hourly_price(total_jam):
    """Tarif per jam: anchor tetap di titik tertentu, di antaranya naik
    Rp5.000/jam dari anchor terdekat di bawahnya."""
    if total_jam > JAM_ANCHORS[-1][0]:
        # Lebih dari jam anchor terakhir (72 jam) -> hitung sebagai sewa harian biasa
        hari = math.ceil(total_jam / 24)
        return compute_daily_price(hari)

    lower_jam, lower_harga = JAM_ANCHORS[0]
    for jam_anchor, harga_anchor in JAM_ANCHORS:
        if total_jam == jam_anchor:
            return harga_anchor
        if total_jam < jam_anchor:
            break
        lower_jam, lower_harga = jam_anchor, harga_anchor

    return lower_harga + (total_jam - lower_jam) * KENAIKAN_PER_JAM


def get_customer_columns():
    global _customer_columns_cache
    if _customer_columns_cache is not None:
        return _customer_columns_cache

    try:
        rows = db.execute_query(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'customers'",
            (Config.MYSQL_CONFIG['database'],),
            fetch=True
        )
        _customer_columns_cache = {row['COLUMN_NAME'] for row in rows}
        return _customer_columns_cache
    except Exception:
        _customer_columns_cache = None
        return set()


def normalize_customer_email(email):
    email = (email or '').strip().lower()
    return email if email and '@' in email else ''


def normalize_phone(phone):
    if not phone:
        return ''
    return ''.join(ch for ch in str(phone) if ch.isdigit())


def build_customer_data(customer):
    if not customer:
        return None
    # Ganti placeholder '-' dengan string kosong, dan None dengan ''
    def clean(val):
        v = str(val) if val is not None else ''
        return '' if v == '-' else v
    return {
        'nama': clean(customer.get('nama', '')),
        'lahir': str(customer.get('tanggal_lahir', '')) if customer.get('tanggal_lahir') else '',
        'jk': customer.get('jenis_kelamin', '') or '',
        'alamat': customer.get('alamat', '') or '',
        'hp': clean(customer.get('no_hp', '')),
        'email': customer.get('email', '') or '',
        'has_password': bool(customer.get('password_hash')),
    }


def customer_profile_complete(customer_data):
    return bool(
        customer_data
        and customer_data.get('nama')
        and customer_data.get('hp')
    )


def upsert_customer_profile(data):
    columns = get_customer_columns()
    payload = {}

    nama = (data.get('nama') or data.get('d-nama') or '').strip()
    lahir = (data.get('lahir') or data.get('d-lahir') or '').strip()
    jk = (data.get('jk') or data.get('d-jk') or '').strip()
    alamat = (data.get('alamat') or data.get('d-alamat') or '').strip()
    hp = normalize_phone(data.get('hp') or data.get('d-hp') or '')
    email = normalize_customer_email(data.get('email') or '')

    if 'nama' in columns:
        payload['nama'] = nama
    if 'no_hp' in columns and hp:
        payload['no_hp'] = hp
    if 'email' in columns and email:
        payload['email'] = email
    if 'tanggal_lahir' in columns:
        payload['tanggal_lahir'] = lahir
    if 'jenis_kelamin' in columns:
        payload['jenis_kelamin'] = jk
    if 'alamat' in columns:
        payload['alamat'] = alamat
    if not payload:
        raise ValueError('Tidak ada kolom customer yang tersedia untuk disimpan')

    if not email and not hp:
        raise ValueError('Email atau nomor HP wajib disertakan')

    customer = None
    if email and hp:
        customer = db.execute_one(
            "SELECT * FROM customers WHERE email = %s OR no_hp = %s",
            (email, hp)
        )
    elif email:
        customer = db.execute_one("SELECT * FROM customers WHERE email = %s", (email,))
    elif hp:
        customer = db.execute_one("SELECT * FROM customers WHERE no_hp = %s", (hp,))

    if customer:
        assignments = [f"{col}=%s" for col in payload.keys()]
        values = list(payload.values()) + [customer['id']]
        db.execute_query(
            f"UPDATE customers SET {', '.join(assignments)} WHERE id=%s",
            tuple(values)
        )
    else:
        columns_list = list(payload.keys())
        placeholders = ', '.join(['%s'] * len(columns_list))
        db.execute_query(
            f"INSERT INTO customers ({', '.join(columns_list)}) VALUES ({placeholders})",
            tuple(payload.values())
        )


@customer_bp.route('/motors', methods=['GET'])
def get_motors_public():
    """Daftar motor untuk halaman customer — motor 'maintenance' disembunyikan
    karena memang tidak bisa disewa customer."""
    motors = db.execute_query(
        "SELECT * FROM motors WHERE status != 'maintenance' "
        "ORDER BY status='tersedia' DESC, nama_motor ASC",
        fetch=True
    )
    for m in motors:
        m['harga_per_hari'] = 50000
    return jsonify({'success': True, 'data': motors})


@customer_bp.route('/customer/profile', methods=['GET', 'POST'])
def save_customer_profile():
    if request.method == 'GET':
        email = normalize_customer_email(request.args.get('email', ''))
        if not email:
            return jsonify({'success': False, 'message': 'Email tidak diberikan'}), 400
        customer = db.execute_one("SELECT * FROM customers WHERE email = %s", (email,))
        if not customer:
            return jsonify({'success': True, 'data': None})
        return jsonify({'success': True, 'data': build_customer_data(customer)})

    data = request.get_json(silent=True) or {}
    if not data and request.form:
        data = request.form.to_dict()

    columns = get_customer_columns()
    required_missing = []
    if 'nama' in columns and not (data.get('nama') or data.get('d-nama')):
        required_missing.append('nama')
    if 'no_hp' in columns and not (data.get('hp') or data.get('d-hp')):
        required_missing.append('no_hp')
    if 'tanggal_lahir' in columns and not (data.get('lahir') or data.get('d-lahir')):
        required_missing.append('tanggal_lahir')
    if 'jenis_kelamin' in columns and not (data.get('jk') or data.get('d-jk')):
        required_missing.append('jenis_kelamin')
    if 'alamat' in columns and not (data.get('alamat') or data.get('d-alamat')):
        required_missing.append('alamat')

    if required_missing:
        return jsonify({'success': False, 'message': 'Semua field wajib diisi'}), 400

    try:
        upsert_customer_profile(data)
    except Exception as exc:
        return jsonify({'success': False, 'message': f'Gagal menyimpan data: {exc}'}), 500

    email = normalize_customer_email(data.get('email') or '')
    hp = normalize_phone(data.get('hp') or data.get('d-hp') or '')
    customer = None
    if email and hp:
        customer = db.execute_one(
            "SELECT * FROM customers WHERE email = %s OR no_hp = %s",
            (email, hp)
        )
    elif email:
        customer = db.execute_one("SELECT * FROM customers WHERE email = %s", (email,))
    elif hp:
        customer = db.execute_one("SELECT * FROM customers WHERE no_hp = %s", (hp,))

    profile_data = build_customer_data(customer) if customer else None

    return jsonify({
        'success': True,
        'message': 'Data customer berhasil disimpan',
        'data': profile_data
    })


@customer_bp.route('/customer/account', methods=['DELETE'])
def delete_customer_account():
    """Customer menghapus akunnya sendiri dari halaman Profil."""
    data = request.get_json(silent=True) or {}
    email = normalize_customer_email(data.get('email') or request.args.get('email', ''))
    if not email:
        return jsonify({'success': False, 'message': 'Email tidak diberikan'}), 400

    customer = db.execute_one("SELECT id FROM customers WHERE email = %s", (email,))
    if not customer:
        return jsonify({'success': False, 'message': 'Akun tidak ditemukan'}), 404

    active = db.execute_one(
        "SELECT COUNT(*) as total FROM bookings WHERE customer_id = %s AND status IN ('pending', 'dikonfirmasi')",
        (customer['id'],)
    )
    if active and active['total'] > 0:
        return jsonify({
            'success': False,
            'message': 'Kamu masih punya booking yang sedang berjalan. Selesaikan dulu sewa motornya sebelum menghapus akun.'
        }), 400

    # Menghapus customer akan otomatis menghapus riwayat booking miliknya (ON DELETE CASCADE)
    db.execute_query("DELETE FROM customers WHERE id = %s", (customer['id'],))
    return jsonify({'success': True, 'message': 'Akun berhasil dihapus'})


def verify_google_id_token(id_token):
    if not Config.GOOGLE_CLIENT_ID:
        raise ValueError('GOOGLE_CLIENT_ID belum dikonfigurasi di environment')
    try:
        with urllib.request.urlopen(
            f'https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(id_token)}'
        ) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        raise ValueError(f'Token Google tidak valid: {exc.code}')
    except Exception as exc:
        raise ValueError(f'Gagal memverifikasi token Google: {exc}')

    if payload.get('aud') != Config.GOOGLE_CLIENT_ID:
        raise ValueError('Token Google tidak cocok dengan aplikasi ini')
    if payload.get('iss') not in ('accounts.google.com', 'https://accounts.google.com'):
        raise ValueError('Issuer Google tidak valid')
    if payload.get('email_verified') not in ('true', True):
        raise ValueError('Email Google belum diverifikasi')

    email = payload.get('email', '').strip().lower()
    if not email:
        raise ValueError('Email Google tidak ditemukan dalam token')
    return email


@customer_bp.route('/customer/google-config', methods=['GET'])
def google_config():
    return jsonify({
        'success': True,
        'google_client_id': Config.GOOGLE_CLIENT_ID or ''
    })


@customer_bp.route('/customer/google-login', methods=['POST'])
def google_login():
    # Login via Google berbeda dari login email+password — tidak butuh password sama sekali.
    data = request.get_json(silent=True) or {}
    id_token = data.get('id_token', '')
    if not id_token:
        return jsonify({'success': False, 'message': 'ID token Google tidak diberikan'}), 400

    try:
        email = verify_google_id_token(id_token)
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400

    customer = db.execute_one("SELECT * FROM customers WHERE email = %s", (email,))
    customer_data = build_customer_data(customer) if customer else None
    if not customer:
        try:
            db.execute_query(
                "INSERT INTO customers (nama, no_hp, email) VALUES (%s, %s, %s)",
                ('-', '-', email)
            )
            customer = db.execute_one("SELECT * FROM customers WHERE email = %s", (email,))
            customer_data = build_customer_data(customer)
        except Exception:
            # Jika sudah ada (race condition), coba ambil lagi
            customer = db.execute_one("SELECT * FROM customers WHERE email = %s", (email,))
            customer_data = build_customer_data(customer) if customer else None
    return jsonify({'success': True, 'message': 'Google account terverifikasi', 'email': email, 'data': customer_data})


@customer_bp.route('/customer/email-login', methods=['POST'])
def email_login():
    """Login dengan email + password (berbeda dari login Google)."""
    data = request.get_json(silent=True) or {}
    email = normalize_customer_email(data.get('email', ''))
    password = data.get('password', '')

    if not email:
        return jsonify({'success': False, 'message': 'Email wajib diisi'}), 400
    if not password:
        return jsonify({'success': False, 'message': 'Password wajib diisi'}), 400

    limiter_key = f'{request.remote_addr}:{email}'
    if _rate_limited(limiter_key):
        return jsonify({
            'success': False,
            'message': 'Terlalu banyak percobaan login. Coba lagi dalam beberapa menit.'
        }), 429

    customer = db.execute_one("SELECT * FROM customers WHERE email = %s", (email,))
    if not customer:
        _record_attempt(limiter_key)
        return jsonify({
            'success': False,
            'message': 'Email belum terdaftar. Silakan buat akun terlebih dahulu.',
            'not_registered': True
        }), 404

    if not customer.get('password_hash'):
        return jsonify({
            'success': False,
            'message': 'Akun ini terdaftar lewat Google. Silakan masuk dengan tombol "Lanjutkan dengan Google".'
        }), 401

    if not check_password_hash(customer['password_hash'], password):
        _record_attempt(limiter_key)
        return jsonify({'success': False, 'message': 'Email atau password salah'}), 401

    customer_data = build_customer_data(customer)
    return jsonify({
        'success': True,
        'message': 'Login berhasil',
        'email': email,
        'data': customer_data,
        'profile_complete': customer_profile_complete(customer_data)
    })


@customer_bp.route('/customer/register', methods=['POST'])
def register_customer():
    """Registrasi akun baru wajib email + password (berbeda dari lanjut dengan Google)."""
    data = request.get_json(silent=True) or {}
    email = normalize_customer_email(data.get('email', ''))
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not email:
        return jsonify({'success': False, 'message': 'Email wajib diisi'}), 400
    if not password:
        return jsonify({'success': False, 'message': 'Password wajib diisi'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Password minimal 6 karakter'}), 400
    if confirm_password and password != confirm_password:
        return jsonify({'success': False, 'message': 'Konfirmasi password tidak cocok'}), 400

    existing = db.execute_one("SELECT id FROM customers WHERE email = %s", (email,))
    if existing:
        return jsonify({
            'success': False,
            'message': 'Email sudah terdaftar. Silakan masuk.',
            'already_registered': True
        }), 409

    try:
        # Gunakan '-' sebagai placeholder untuk kolom NOT NULL (nama, no_hp)
        # Data lengkap akan diisi setelah customer melengkapi profil
        db.execute_query(
            "INSERT INTO customers (nama, no_hp, email, password_hash) VALUES (%s, %s, %s, %s)",
            ('-', '-', email, generate_password_hash(password))
        )
    except Exception as exc:
        return jsonify({'success': False, 'message': f'Gagal mendaftar: {exc}'}), 500

    customer = db.execute_one("SELECT * FROM customers WHERE email = %s", (email,))
    customer_data = build_customer_data(customer)
    return jsonify({
        'success': True,
        'message': 'Registrasi berhasil. Lengkapi data diri Anda.',
        'email': email,
        'data': customer_data
    }), 201


@customer_bp.route('/motors/<int:motor_id>', methods=['GET'])
def get_motor_detail(motor_id):
    motor = db.execute_one("SELECT * FROM motors WHERE id = %s", (motor_id,))
    if not motor:
        return jsonify({'success': False, 'message': 'Motor tidak ditemukan'}), 404
    motor['harga_per_hari'] = 50000
    return jsonify({'success': True, 'data': motor})


@customer_bp.route('/booking', methods=['POST'])
def create_booking():
    # Import di sini untuk menghindari circular import
    from Backend.sse import push_event

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({'success': False, 'message': 'Payload JSON tidak valid'}), 400

    required = ['nama', 'no_hp', 'motor_id', 'tanggal_mulai']
    for field in required:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'{field} wajib diisi'}), 400
    data['no_hp'] = normalize_phone(data.get('no_hp'))
    if not data['no_hp']:
        return jsonify({'success': False, 'message': 'Nomor HP tidak valid'}), 400

    jenis_sewa = data.get('jenis_sewa', 'harian')
    if jenis_sewa not in ('harian', 'paket'):
        return jsonify({'success': False, 'message': 'Jenis sewa tidak valid'}), 400

    # Cek motor masih tersedia
    motor = db.execute_one(
        "SELECT * FROM motors WHERE id = %s AND status = 'tersedia'",
        (data['motor_id'],)
    )
    if not motor:
        return jsonify({'success': False, 'message': 'Motor tidak tersedia untuk dipesan'}), 400

    tgl_mulai = datetime.strptime(data['tanggal_mulai'], '%Y-%m-%d').date()
    jam_mulai_val = None
    jam_selesai_val = None
    durasi_jam_val = None
    paket_label_val = None

    if jenis_sewa == 'paket':
        # ── Sewa per jam (freeform): cukup tanggal, jam mulai & jam selesai ──
        jam_mulai_str   = data.get('jam_mulai')
        jam_selesai_str = data.get('jam_selesai')
        if not jam_mulai_str or not jam_selesai_str:
            return jsonify({'success': False, 'message': 'Jam mulai dan jam selesai wajib diisi'}), 400
        try:
            jam_mulai_val   = datetime.strptime(jam_mulai_str, '%H:%M').time()
            jam_selesai_val = datetime.strptime(jam_selesai_str, '%H:%M').time()
        except ValueError:
            return jsonify({'success': False, 'message': 'Format jam tidak valid'}), 400

        mulai_dt = datetime.combine(tgl_mulai, jam_mulai_val)
        # Jika jam selesai <= jam mulai, dianggap menyeberang ke hari berikutnya
        tgl_selesai_jam = tgl_mulai if jam_selesai_val > jam_mulai_val else tgl_mulai + timedelta(days=1)
        selesai_dt = datetime.combine(tgl_selesai_jam, jam_selesai_val)

        durasi_jam_val = math.ceil((selesai_dt - mulai_dt).total_seconds() / 3600)
        if durasi_jam_val <= 0:
            return jsonify({'success': False, 'message': 'Jam selesai harus setelah jam mulai'}), 400

        tgl_selesai = selesai_dt.date()
        total_hari  = max(1, math.ceil(durasi_jam_val / 24))
        total_harga = compute_hourly_price(durasi_jam_val)
        paket_label_val = f'{durasi_jam_val} Jam'
    else:
        # ── Sewa per hari: tanggal + jam mulai & jam selesai (opsional) ──
        if not data.get('tanggal_selesai'):
            return jsonify({'success': False, 'message': 'tanggal_selesai wajib diisi'}), 400
        tgl_selesai = datetime.strptime(data['tanggal_selesai'], '%Y-%m-%d').date()
        if tgl_selesai < tgl_mulai:
            return jsonify({'success': False, 'message': 'Tanggal selesai tidak boleh sebelum tanggal mulai'}), 400

        jam_mulai_str   = data.get('jam_mulai')
        jam_selesai_str = data.get('jam_selesai')
        if jam_mulai_str:
            try:
                jam_mulai_val = datetime.strptime(jam_mulai_str, '%H:%M').time()
            except ValueError:
                return jsonify({'success': False, 'message': 'Format jam mulai tidak valid'}), 400
        if jam_selesai_str:
            try:
                jam_selesai_val = datetime.strptime(jam_selesai_str, '%H:%M').time()
            except ValueError:
                return jsonify({'success': False, 'message': 'Format jam selesai tidak valid'}), 400

        # Sewa harian dihitung inklusif: mulai tanggal 6 s/d tanggal 8 = 3 hari
        total_hari  = (tgl_selesai - tgl_mulai).days + 1
        total_harga = compute_daily_price(total_hari)

    # Buat atau cari customer
    customer = db.execute_one("SELECT * FROM customers WHERE no_hp = %s", (data['no_hp'],))
    if customer:
        customer_id = customer['id']
        db.execute_query(
            "UPDATE customers SET nama=%s, email=%s WHERE id=%s",
            (data['nama'], data.get('email', ''), customer_id)
        )
    else:
        customer_id = db.execute_query(
            "INSERT INTO customers (nama, no_hp, email) VALUES (%s, %s, %s)",
            (data['nama'], data['no_hp'], data.get('email', ''))
        )
        if customer_id is True or not customer_id:
            customer = db.execute_one("SELECT * FROM customers WHERE no_hp = %s", (data['no_hp'],))
            if not customer:
                return jsonify({'success': False, 'message': 'Gagal menyimpan data customer'}), 500
            customer_id = customer['id']

    # Simpan booking
    booking_id = db.execute_query(
        """INSERT INTO bookings (motor_id, customer_id, jenis_sewa, tanggal_mulai, jam_mulai,
           jam_selesai, durasi_jam, paket_label, tanggal_selesai, total_hari, total_harga, catatan)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (data['motor_id'], customer_id, jenis_sewa, tgl_mulai, jam_mulai_val, jam_selesai_val,
         durasi_jam_val, paket_label_val, tgl_selesai, total_hari, total_harga,
         data.get('catatan', ''))
    )

    # ── Push notifikasi real-time ke semua admin yang sedang buka halaman ──
    if booking_id is True or not booking_id:
        latest_booking = db.execute_one(
            """SELECT id FROM bookings
               WHERE customer_id = %s AND motor_id = %s
               ORDER BY created_at DESC, id DESC
               LIMIT 1""",
            (customer_id, data['motor_id'])
        )
        booking_id = latest_booking['id'] if latest_booking else None

    push_event('admin', 'new_booking', {
        'booking_id':  booking_id,
        'nama':        data['nama'],
        'no_hp':       data['no_hp'],
        'motor':       motor['nama_motor'],
        'jenis_sewa':  jenis_sewa,
        'paket_label': paket_label_val,
        'total_hari':  total_hari,
        'total_harga': total_harga,
        'tanggal_mulai':   str(tgl_mulai),
        'tanggal_selesai': str(tgl_selesai),
    })

    return jsonify({
        'success': True,
        'message': 'Booking berhasil dibuat! Tunggu konfirmasi dari Kurnia Rental.',
        'data': {
            'booking_id': booking_id,
            'motor':      motor['nama_motor'],
            'jenis_sewa': jenis_sewa,
            'total_hari': total_hari,
            'total_harga': total_harga
        }
    }), 201


@customer_bp.route('/booking/cek', methods=['GET'])
def cek_booking():
    no_hp = request.args.get('no_hp', '').strip()
    if not no_hp:
        return jsonify({'success': False, 'message': 'Nomor HP wajib diisi'}), 400

    customer = db.execute_one("SELECT id FROM customers WHERE no_hp = %s", (no_hp,))
    if not customer:
        return jsonify({'success': True, 'data': []})

    bookings = _get_bookings_for_customer(customer['id'])
    return jsonify({'success': True, 'data': bookings})


@customer_bp.route('/customer/riwayat', methods=['GET'])
def riwayat_customer():
    """Riwayat booking milik customer yang sedang login (dicari via email/no_hp)."""
    email = normalize_customer_email(request.args.get('email', ''))
    no_hp = normalize_phone(request.args.get('no_hp', ''))

    customer = None
    if email:
        customer = db.execute_one("SELECT id FROM customers WHERE email = %s", (email,))
    if not customer and no_hp:
        customer = db.execute_one("SELECT id FROM customers WHERE no_hp = %s", (no_hp,))

    if not customer:
        return jsonify({'success': True, 'data': []})

    bookings = _get_bookings_for_customer(customer['id'])
    return jsonify({'success': True, 'data': bookings})


def _get_bookings_for_customer(customer_id):
    bookings = db.execute_query(
        """SELECT b.id, b.jenis_sewa, b.tanggal_mulai, b.jam_mulai, b.jam_selesai,
                  b.tanggal_selesai, b.total_hari, b.total_harga, b.denda, b.status,
                  b.catatan, b.created_at, b.waktu_kembali,
                  m.nama_motor, m.merk, m.plat_nomor
           FROM bookings b
           JOIN motors m ON b.motor_id = m.id
           WHERE b.customer_id = %s
           ORDER BY b.created_at DESC""",
        (customer_id,), fetch=True
    )
    for b in bookings:
        b['total_harga']     = float(b['total_harga'])
        b['denda']           = float(b.get('denda') or 0)
        b['tanggal_mulai']   = str(b['tanggal_mulai'])
        b['tanggal_selesai'] = str(b['tanggal_selesai'])
        b['jam_mulai']       = str(b['jam_mulai']) if b.get('jam_mulai') else ''
        b['jam_selesai']     = str(b['jam_selesai']) if b.get('jam_selesai') else ''
        b['created_at']      = str(b['created_at'])
        b['waktu_kembali']   = str(b['waktu_kembali']) if b.get('waktu_kembali') else ''
    return bookings
