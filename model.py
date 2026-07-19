import mysql.connector
from mysql.connector import pooling
from config import Config
import logging

# PENTING: level DEBUG di sini akan membuat mysql-connector mencetak log
# super detail (isi paket jaringan) untuk SETIAP query — ini bikin setiap
# request yang sentuh database terasa lambat. Pakai WARNING untuk normal,
# ganti ke DEBUG sendiri kalau memang lagi troubleshooting koneksi DB.
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class Database:
    """Singleton connection pool ke MySQL."""
    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._pool is None:
            self._pool = pooling.MySQLConnectionPool(
                pool_name="kurnia_pool",
                pool_size=5,
                pool_reset_session=True,
                **Config.MYSQL_CONFIG
            )

    def get_connection(self):
        return self._pool.get_connection()

    def execute_query(self, query, params=None, fetch=False):
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            if fetch:
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.lastrowid if cursor.lastrowid else True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def execute_one(self, query, params=None):
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()
