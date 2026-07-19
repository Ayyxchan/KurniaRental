from flask import Blueprint, request, jsonify
from Backend.admin.login import login_required
from model import Database

customers_bp = Blueprint('customers', __name__)
db = Database()


@customers_bp.route('/admin/customers', methods=['GET'])
@login_required
def get_customers():
    customers = db.execute_query(
        "SELECT id, nama, no_hp, email, tanggal_lahir, jenis_kelamin, alamat, created_at "
        "FROM customers ORDER BY created_at DESC",
        fetch=True
    )
    for c in customers:
        if c.get('tanggal_lahir') is not None:
            c['tanggal_lahir'] = str(c['tanggal_lahir'])
        if c.get('created_at') is not None:
            c['created_at'] = str(c['created_at'])
    return jsonify({'success': True, 'data': customers})


@customers_bp.route('/admin/customers/<int:customer_id>', methods=['PUT'])
@login_required
def update_customer(customer_id):
    data = request.get_json(silent=True) or {}
    if not data.get('nama') or not data.get('no_hp'):
        return jsonify({'success': False, 'message': 'Nama dan nomor HP wajib diisi'}), 400

    db.execute_query(
        "UPDATE customers SET nama=%s, no_hp=%s, email=%s, tanggal_lahir=%s, jenis_kelamin=%s, alamat=%s WHERE id=%s",
        (
            data['nama'],
            data['no_hp'],
            data.get('email', ''),
            data.get('tanggal_lahir') or None,
            data.get('jenis_kelamin', ''),
            data.get('alamat', ''),
            customer_id
        )
    )
    return jsonify({'success': True, 'message': 'Data customer berhasil diperbarui'})


@customers_bp.route('/admin/customers/<int:customer_id>', methods=['DELETE'])
@login_required
def delete_customer(customer_id):
    db.execute_query("DELETE FROM customers WHERE id = %s", (customer_id,))
    return jsonify({'success': True, 'message': 'Customer berhasil dihapus'})
