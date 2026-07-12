import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'kurnia-rental-secret-key-2024')
    # PENTING: default DEBUG harus False. Jangan pernah set FLASK_DEBUG=True
    # di server production — mode debug membuka Werkzeug interactive debugger
    # yang bisa dipakai orang lain untuk menjalankan kode di server kamu.
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'

    MYSQL_CONFIG = {
        'host':     os.getenv('DB_HOST', 'localhost'),
        'port':     int(os.getenv('DB_PORT', 3306)),
        'user':     os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'kurnia_rental'),
        'charset':  'utf8mb4',
    }

    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    ADMIN_DEFAULT_USERNAME = os.getenv('ADMIN_DEFAULT_USERNAME', 'admin')
    ADMIN_DEFAULT_PASSWORD = os.getenv('ADMIN_DEFAULT_PASSWORD', 'admin123')

    # Cloudinary — untuk upload foto motor
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY    = os.getenv('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')

    # Keamanan cookie session admin
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Aktif otomatis kalau bukan mode debug (di production biasanya diakses via HTTPS)
    SESSION_COOKIE_SECURE = not DEBUG
