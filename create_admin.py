"""
Jalankan sekali untuk membuat akun admin pertama:
    python create_admin.py
"""
from werkzeug.security import generate_password_hash
from model import Database

def main():
    db = Database()
    username = input("Username admin: ").strip()
    password = input("Password admin: ").strip()

    if not username or not password:
        print("Username dan password tidak boleh kosong.")
        return

    existing = db.execute_one("SELECT id FROM admins WHERE username = %s", (username,))
    if existing:
        print(f"Username '{username}' sudah ada.")
        return

    hashed = generate_password_hash(password)
    db.execute_query(
        "INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
        (username, hashed)
    )
    print(f"Admin '{username}' berhasil dibuat!")

if __name__ == '__main__':
    main()
