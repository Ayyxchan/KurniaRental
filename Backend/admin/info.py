from flask import Blueprint, request, jsonify
from model import Database
from Backend.admin.login import login_required

info_bp = Blueprint('info', __name__)
db = Database()


def _serialize(row):
    row['created_at'] = str(row['created_at']) if row.get('created_at') else ''
    row['updated_at'] = str(row['updated_at']) if row.get('updated_at') else ''
    return row


# ── Admin: kelola informasi sistem ──
@info_bp.route('/admin/info', methods=['GET'])
@login_required
def admin_list_info():
    rows = db.execute_query(
        "SELECT * FROM site_info ORDER BY urutan ASC, id ASC", fetch=True
    )
    return jsonify({'success': True, 'data': [_serialize(r) for r in rows]})


@info_bp.route('/admin/info', methods=['POST'])
@login_required
def admin_add_info():
    data = request.get_json(silent=True) or {}
    isi = (data.get('isi') or '').strip()
    if not isi:
        return jsonify({'success': False, 'message': 'Isi informasi wajib diisi'}), 400
    urutan = data.get('urutan', 0)
    new_id = db.execute_query(
        "INSERT INTO site_info (isi, urutan) VALUES (%s, %s)", (isi, urutan)
    )
    return jsonify({'success': True, 'message': 'Informasi berhasil ditambahkan', 'id': new_id}), 201


@info_bp.route('/admin/info/<int:info_id>', methods=['PUT'])
@login_required
def admin_update_info(info_id):
    data = request.get_json(silent=True) or {}
    isi = (data.get('isi') or '').strip()
    if not isi:
        return jsonify({'success': False, 'message': 'Isi informasi wajib diisi'}), 400
    urutan = data.get('urutan', 0)
    db.execute_query(
        "UPDATE site_info SET isi=%s, urutan=%s WHERE id=%s", (isi, urutan, info_id)
    )
    return jsonify({'success': True, 'message': 'Informasi berhasil diperbarui'})


@info_bp.route('/admin/info/<int:info_id>', methods=['DELETE'])
@login_required
def admin_delete_info(info_id):
    db.execute_query("DELETE FROM site_info WHERE id=%s", (info_id,))
    return jsonify({'success': True, 'message': 'Informasi berhasil dihapus'})


# ── Publik: dipakai halaman Home aplikasi customer ──
@info_bp.route('/info', methods=['GET'])
def public_list_info():
    rows = db.execute_query(
        "SELECT id, isi FROM site_info ORDER BY urutan ASC, id ASC", fetch=True
    )
    return jsonify({'success': True, 'data': rows})
