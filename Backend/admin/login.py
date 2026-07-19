from flask import Blueprint, request, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash
from model import Database
from config import Config
import time

login_bp = Blueprint('login', __name__)
db = Database()

# ── Rate limiter sederhana untuk cegah brute-force login ──
# Catatan: ini in-memory (reset kalau server restart / tidak sinkron antar worker).
# Untuk produksi skala besar, pertimbangkan Flask-Limiter + Redis.
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


def ensure_default_admin():
    existing = db.execute_one("SELECT id FROM admins LIMIT 1")
    if existing:
        return
    db.execute_query(
        "INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
        (
            Config.ADMIN_DEFAULT_USERNAME,
            generate_password_hash(Config.ADMIN_DEFAULT_PASSWORD)
        )
    )


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({'success': False, 'message': 'Silakan login terlebih dahulu'}), 401
        return f(*args, **kwargs)
    return decorated


@login_bp.route('/admin/login', methods=['POST'])
def login():
    ensure_default_admin()
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username dan password wajib diisi'}), 400

    limiter_key = f'{request.remote_addr}:{username}'
    if _rate_limited(limiter_key):
        return jsonify({
            'success': False,
            'message': 'Terlalu banyak percobaan login. Coba lagi dalam beberapa menit.'
        }), 429

    admin = db.execute_one(
        "SELECT * FROM admins WHERE username = %s", (username,)
    )

    if not admin or not check_password_hash(admin['password_hash'], password):
        _record_attempt(limiter_key)
        return jsonify({'success': False, 'message': 'Username atau password salah'}), 401

    session['admin_id'] = admin['id']
    session['admin_username'] = admin['username']
    session.permanent = True

    return jsonify({'success': True, 'message': 'Login berhasil', 'username': admin['username']})


@login_bp.route('/admin/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logout berhasil'})


@login_bp.route('/admin/account', methods=['PUT'])
@login_required
def update_account():
    data = request.get_json(silent=True) or {}
    current_password = data.get('current_password', '')
    new_username = data.get('username', '').strip()
    new_password = data.get('password', '')

    if not current_password:
        return jsonify({'success': False, 'message': 'Password lama wajib diisi'}), 400

    admin = db.execute_one("SELECT * FROM admins WHERE id = %s", (session['admin_id'],))
    if not admin or not check_password_hash(admin['password_hash'], current_password):
        return jsonify({'success': False, 'message': 'Password lama salah'}), 401

    if not new_username and not new_password:
        return jsonify({'success': False, 'message': 'Masukkan username baru atau password baru'}), 400

    if new_username and new_username != admin['username']:
        existing = db.execute_one("SELECT id FROM admins WHERE username = %s", (new_username,))
        if existing:
            return jsonify({'success': False, 'message': 'Username sudah digunakan'}), 400
        db.execute_query("UPDATE admins SET username = %s WHERE id = %s", (new_username, admin['id']))
        session['admin_username'] = new_username

    if new_password:
        db.execute_query(
            "UPDATE admins SET password_hash = %s WHERE id = %s",
            (generate_password_hash(new_password), admin['id'])
        )

    return jsonify({'success': True, 'message': 'Informasi akun berhasil diperbarui'})


@login_bp.route('/admin/auth/check', methods=['GET'])
def auth_check():
    ensure_default_admin()
    if 'admin_id' in session:
        return jsonify({'logged_in': True, 'username': session.get('admin_username')})
    return jsonify({'logged_in': False}), 401
