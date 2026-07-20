from flask import Blueprint, request, jsonify
from model import Database
from Backend.admin.login import login_required
from Backend.sse import push_event

motors_bp = Blueprint('motors', __name__)
db = Database()


@motors_bp.route('/admin/motors', methods=['GET'])
@login_required
def get_motors():
    motors = db.execute_query(
        "SELECT * FROM motors ORDER BY created_at DESC", fetch=True
    )
    return jsonify({'success': True, 'data': motors})


@motors_bp.route('/admin/motors', methods=['POST'])
@login_required
def add_motor():
    data = request.get_json()
    required = ['nama_motor', 'merk']
    for field in required:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'{field} wajib diisi'}), 400

    plat_nomor = (data.get('plat_nomor') or '').strip()
    if plat_nomor:
        existing = db.execute_one(
            "SELECT id FROM motors WHERE plat_nomor = %s", (plat_nomor,)
        )
        if existing:
            return jsonify({'success': False, 'message': f'Plat nomor "{plat_nomor}" sudah dipakai motor lain'}), 409

    motor_id = db.execute_query(
        """INSERT INTO motors (nama_motor, merk, plat_nomor, tahun, status, deskripsi, gambar_url)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (data['nama_motor'], data['merk'], plat_nomor, data.get('tahun'),
         data.get('status', 'tersedia'),
         data.get('deskripsi', ''), data.get('gambar_url', ''))
    )
    return jsonify({'success': True, 'message': 'Motor berhasil ditambahkan', 'id': motor_id}), 201


@motors_bp.route('/admin/motors/<int:motor_id>', methods=['PUT'])
@login_required
def update_motor(motor_id):
    data = request.get_json()

    plat_nomor = (data.get('plat_nomor') or '').strip()
    if plat_nomor:
        existing = db.execute_one(
            "SELECT id FROM motors WHERE plat_nomor = %s AND id != %s", (plat_nomor, motor_id)
        )
        if existing:
            return jsonify({'success': False, 'message': f'Plat nomor "{plat_nomor}" sudah dipakai motor lain'}), 409

    db.execute_query(
        """UPDATE motors SET nama_motor=%s, merk=%s, plat_nomor=%s, tahun=%s,
           status=%s, deskripsi=%s, gambar_url=%s WHERE id=%s""",
        (data['nama_motor'], data['merk'], plat_nomor, data.get('tahun'),
         data.get('status', 'tersedia'),
         data.get('deskripsi', ''), data.get('gambar_url', ''), motor_id)
    )

    motor = db.execute_one("SELECT * FROM motors WHERE id = %s", (motor_id,))
    if motor:
        push_event('customer', 'motor_update', {
            'motor_id': motor['id'],
            'nama_motor': motor['nama_motor'],
            'status': motor['status'],
        })

    return jsonify({'success': True, 'message': 'Motor berhasil diperbarui'})


@motors_bp.route('/admin/motors/<int:motor_id>', methods=['DELETE'])
@login_required
def delete_motor(motor_id):
    db.execute_query("DELETE FROM motors WHERE id = %s", (motor_id,))
    return jsonify({'success': True, 'message': 'Motor berhasil dihapus'})


@motors_bp.route('/admin/motors/<int:motor_id>/status', methods=['PATCH'])
@login_required
def update_status(motor_id):
    data = request.get_json() or {}
    status = data.get('status')
    if status not in ['tersedia', 'disewa', 'maintenance']:
        return jsonify({'success': False, 'message': 'Status tidak valid'}), 400
    db.execute_query("UPDATE motors SET status=%s WHERE id=%s", (status, motor_id))

    motor = db.execute_one("SELECT * FROM motors WHERE id = %s", (motor_id,))
    if motor:
        push_event('customer', 'motor_update', {
            'motor_id': motor['id'],
            'nama_motor': motor['nama_motor'],
            'status': motor['status'],
        })

    return jsonify({'success': True, 'message': f'Status motor diubah ke {status}'})
