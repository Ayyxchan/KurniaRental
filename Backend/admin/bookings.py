from flask import Blueprint, request, jsonify
from model import Database
from Backend.admin.login import login_required
from datetime import datetime, time as dtime, timedelta
import math

bookings_bp = Blueprint('bookings', __name__)
db = Database()

TARIF_HARIAN = 50000
DENDA_PER_JAM = 5000  # denda keterlambatan pengembalian motor, per jam kelebihan


def now_wib():
    """Server Vercel jalan di zona UTC, sementara semua jam yang diinput
    customer/admin itu WIB (UTC+7). Pakai fungsi ini setiap butuh 'jam
    sekarang' supaya konsisten dibandingkan dengan tanggal_selesai/jam_selesai
    dkk yang tersimpan sebagai jam WIB apa adanya."""
    return datetime.utcnow() + timedelta(hours=7)


@bookings_bp.route('/admin/bookings', methods=['GET'])
@login_required
def get_bookings():
    bookings = db.execute_query(
        """SELECT b.*,
                  COALESCE(m.nama_motor, 'Motor tidak ditemukan') AS nama_motor,
                  COALESCE(m.merk, '-') AS merk,
                  COALESCE(m.plat_nomor, '-') AS plat_nomor,
                  COALESCE(c.nama, b.nama_pelanggan, 'Akun sudah dihapus') AS nama_customer,
                  COALESCE(c.no_hp, b.no_hp_pelanggan, '-') AS no_hp
           FROM bookings b
           LEFT JOIN motors m ON b.motor_id = m.id
           LEFT JOIN customers c ON b.customer_id = c.id
           ORDER BY b.created_at DESC""",
        fetch=True
    )
    # Serialisasi agar JSON-safe
    for b in bookings:
        b['total_harga']     = float(b['total_harga'])
        b['denda']           = float(b.get('denda') or 0)
        b['tanggal_mulai']   = str(b['tanggal_mulai'])
        b['tanggal_selesai'] = str(b['tanggal_selesai'])
        b['jam_mulai']       = str(b['jam_mulai']) if b.get('jam_mulai') else ''
        b['jam_selesai']     = str(b['jam_selesai']) if b.get('jam_selesai') else ''
        b['created_at']      = str(b['created_at'])
        b['updated_at']      = str(b['updated_at']) if b.get('updated_at') else ''
        b['waktu_kembali']   = str(b['waktu_kembali']) if b.get('waktu_kembali') else ''
    return jsonify({'success': True, 'data': bookings})


@bookings_bp.route('/admin/bookings/<int:booking_id>/status', methods=['PATCH'])
@login_required
def update_booking_status(booking_id):
    from Backend.sse import push_event

    data   = request.get_json()
    status = data.get('status')
    valid  = ['pending', 'dikonfirmasi', 'selesai', 'dibatalkan']
    if status not in valid:
        return jsonify({'success': False, 'message': 'Status tidak valid'}), 400

    booking = db.execute_one("SELECT * FROM bookings WHERE id = %s", (booking_id,))
    if not booking:
        return jsonify({'success': False, 'message': 'Booking tidak ditemukan'}), 404

    denda = float(booking.get('denda') or 0)
    waktu_kembali = None

    if status == 'selesai':
        # Hitung denda jika motor dikembalikan setelah jadwal selesai sewa
        waktu_kembali = now_wib()
        jam_selesai = booking.get('jam_selesai') or dtime(23, 59, 59)
        if hasattr(jam_selesai, 'total_seconds'):
            # mysql-connector kadang mengembalikan timedelta untuk kolom TIME
            total_sec = int(jam_selesai.total_seconds())
            jam_selesai = dtime(hour=(total_sec // 3600) % 24,
                                 minute=(total_sec // 60) % 60,
                                 second=total_sec % 60)
        jadwal_selesai_dt = datetime.combine(booking['tanggal_selesai'], jam_selesai)
        if waktu_kembali > jadwal_selesai_dt:
            telat_jam = (waktu_kembali - jadwal_selesai_dt).total_seconds() / 3600
            telat_jam_bulat = math.ceil(telat_jam)  # tiap kelebihan menit dibulatkan ke atas 1 jam
            denda = telat_jam_bulat * DENDA_PER_JAM
        else:
            denda = 0

        db.execute_query(
            "UPDATE bookings SET status=%s, denda=%s, waktu_kembali=%s WHERE id=%s",
            (status, denda, waktu_kembali, booking_id)
        )
    else:
        db.execute_query("UPDATE bookings SET status=%s WHERE id=%s", (status, booking_id))

    # Update status motor otomatis + ambil info motor untuk SSE
    motor = db.execute_one("SELECT * FROM motors WHERE id = %s", (booking['motor_id'],))
    new_motor_status = motor['status'] if motor else 'tersedia'

    if status == 'dikonfirmasi':
        new_motor_status = 'disewa'
        db.execute_query("UPDATE motors SET status='disewa' WHERE id=%s", (booking['motor_id'],))
    elif status in ['selesai', 'dibatalkan']:
        new_motor_status = 'tersedia'
        db.execute_query("UPDATE motors SET status='tersedia' WHERE id=%s", (booking['motor_id'],))

    # ── Push update ke semua customer yang sedang buka halaman ──
    # Supaya status motor langsung berubah tanpa customer perlu refresh
    if motor:
        from Backend.sse import push_event as _push
        _push('customer', 'motor_update', {
            'motor_id':     motor['id'],
            'nama_motor':   motor['nama_motor'],
            'status':       new_motor_status,
            'booking_status': status,
        })

    msg = f'Status booking diubah ke {status}'
    if status == 'selesai' and denda > 0:
        msg += f'. Motor terlambat dikembalikan, denda Rp {denda:,.0f}'.replace(',', '.')

    return jsonify({'success': True, 'message': msg, 'denda': denda})


@bookings_bp.route('/admin/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    total_motor  = db.execute_one("SELECT COUNT(*) as total FROM motors")['total']
    total_booking = db.execute_one("SELECT COUNT(*) as total FROM bookings")['total']
    pending      = db.execute_one("SELECT COUNT(*) as total FROM bookings WHERE status='pending'")['total']
    pendapatan   = db.execute_one(
        "SELECT COALESCE(SUM(total_harga + denda), 0) as total FROM bookings WHERE status='selesai'"
    )['total']

    return jsonify({
        'success': True,
        'data': {
            'total_motor':      total_motor,
            'total_booking':    total_booking,
            'pending_booking':  pending,
            'total_pendapatan': float(pendapatan)
        }
    })
