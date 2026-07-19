import cloudinary
import cloudinary.uploader
from flask import Blueprint, request, jsonify
from config import Config
from Backend.admin.login import login_required

upload_bp = Blueprint('upload', __name__)

# Inisialisasi Cloudinary sekali saat modul di-import
cloudinary.config(
    cloud_name = Config.CLOUDINARY_CLOUD_NAME,
    api_key    = Config.CLOUDINARY_API_KEY,
    api_secret = Config.CLOUDINARY_API_SECRET,
    secure     = True
)


@upload_bp.route('/admin/upload/motor', methods=['POST'])
@login_required
def upload_motor_image():
    """
    Upload foto motor ke Cloudinary.
    Terima multipart/form-data dengan field 'file'.
    Return URL gambar yang bisa langsung disimpan ke kolom gambar_url di tabel motors.
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'File tidak ditemukan'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Tidak ada file yang dipilih'}), 400

    # Validasi tipe file
    allowed = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
    if file.content_type not in allowed:
        return jsonify({'success': False, 'message': 'Hanya file gambar (JPG/PNG/WebP) yang diizinkan'}), 400

    try:
        result = cloudinary.uploader.upload(
            file,
            folder='kurnia_rental/motors',   # folder di Cloudinary
            transformation=[
                {'width': 800, 'height': 600, 'crop': 'fill', 'quality': 'auto'},
            ]
        )
        return jsonify({
            'success': True,
            'url':     result['secure_url'],
            'public_id': result['public_id'],
            'message': 'Foto berhasil diupload'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Upload gagal: {str(e)}'}), 500
