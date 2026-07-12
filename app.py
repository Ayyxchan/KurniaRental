from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from config import Config
from datetime import timedelta
import os

from Backend.admin.login    import login_bp
from Backend.admin.motors   import motors_bp
from Backend.admin.bookings import bookings_bp
from Backend.admin.upload   import upload_bp
from Backend.admin.customers import customers_bp
from Backend.admin.info     import info_bp
from Backend.customer.customer import customer_bp
from Backend.sse            import sse_bp


def create_app():
    app = Flask(
        __name__,
        static_folder='Frontend',
        template_folder='.'
    )
    app.config.from_object(Config)
    app.permanent_session_lifetime = timedelta(hours=24)

    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Register blueprints
    app.register_blueprint(login_bp,    url_prefix='/api')
    app.register_blueprint(motors_bp,   url_prefix='/api')
    app.register_blueprint(bookings_bp, url_prefix='/api')
    app.register_blueprint(upload_bp,   url_prefix='/api')
    app.register_blueprint(customers_bp, url_prefix='/api')
    app.register_blueprint(info_bp,     url_prefix='/api')
    app.register_blueprint(customer_bp, url_prefix='/api')
    app.register_blueprint(sse_bp,      url_prefix='/api')

    # ---- Routing halaman Frontend ----

    @app.route('/')
    def index():
        customer_index = os.path.join(app.root_path, 'Frontend', 'customer', 'index.html')
        if os.path.exists(customer_index):
            return send_from_directory(os.path.join(app.root_path, 'Frontend', 'customer'), 'index.html')
        return "Aplikasi berjalan, tetapi file frontend customer/index.html tidak ditemukan.", 404

    @app.route('/customer/')
    @app.route('/customer')
    def customer_root():
        # Tampilkan langsung isi aplikasi (mode tamu bisa lihat-lihat motor
        # tanpa wajib login). Login/daftar tetap bisa diakses lewat ikon di
        # sidebar, yang mengarah ke /customer/login.html.
        return send_from_directory(
            os.path.join(app.root_path, 'Frontend', 'customer'), 'index.html'
        )

    @app.route('/customer/<path:filename>')
    def customer_pages(filename):
        # Jika user mengakses tanpa ekstensi (mis. /customer/home), tambahkan .html
        safe_name = os.path.normpath(filename)
        # normalisasi agar selalu gunakan forward slash untuk send_from_directory
        safe_name = safe_name.replace('\\', '/')
        if safe_name.startswith('..') or os.path.isabs(safe_name):
            return send_from_directory(
                os.path.join(app.root_path, 'Frontend', 'customer'), 'index.html'
            )
        if not os.path.splitext(safe_name)[1]:
            safe_name = safe_name + '.html'
        return send_from_directory(
            os.path.join(app.root_path, 'Frontend', 'customer'), safe_name
        )

    # Serve customer CSS explicitly (fix Windows path issues)
    @app.route('/customer/css/<path:filename>')
    def customer_css(filename):
        return send_from_directory(
            os.path.join(app.root_path, 'Frontend', 'customer', 'css'), filename
        )

    @app.route('/admin/')
    @app.route('/admin')
    def admin_root():
        return send_from_directory(
            os.path.join(app.root_path, 'Frontend', 'admin'), 'login.html'
        )

    @app.route('/admin/<path:filename>')
    @app.route('/admin/<path:filename>/')
    def admin_pages(filename):
        safe_name = os.path.normpath(filename)
        safe_name = safe_name.replace('\\', '/')
        if safe_name.startswith('..') or os.path.isabs(safe_name):
            return send_from_directory(
                os.path.join(app.root_path, 'Frontend', 'admin'), 'login.html'
            )
        if not os.path.splitext(safe_name)[1]:
            safe_name = safe_name + '.html'
        return send_from_directory(
            os.path.join(app.root_path, 'Frontend', 'admin'), safe_name
        )

    @app.route('/admin/css/<path:filename>')
    @app.route('/admin/css/<path:filename>/')
    def admin_css(filename):
        return send_from_directory(
            os.path.join(app.root_path, 'Frontend', 'admin', 'css'), filename
        )

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Route tidak ditemukan'}), 404
        customer_index = os.path.join(app.root_path, 'Frontend', 'customer', 'index.html')
        if os.path.exists(customer_index):
            return send_from_directory(os.path.join(app.root_path, 'Frontend', 'customer'), 'index.html')
        return "Aplikasi berjalan, tetapi file frontend customer/index.html tidak ditemukan.", 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Terjadi kesalahan server'}), 500

    return app


# Objek module-level "app" ini WAJIB ada di luar blok if __name__ == '__main__'
# supaya server production (gunicorn) bisa menemukannya lewat perintah:
#   gunicorn app:app
# app.run() di bawah cuma dipakai saat development lokal (python app.py).
app = create_app()

if __name__ == '__main__':
    # threaded=True wajib untuk SSE supaya tiap koneksi punya thread sendiri
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000, threaded=True)
