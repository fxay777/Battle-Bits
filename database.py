import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Create purchases table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            items_json TEXT NOT NULL,
            total_price REAL NOT NULL,
            payment_method TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Create a default admin user if it doesn't exist
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        from werkzeug.security import generate_password_hash
        admin_pass = generate_password_hash('123')
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
            ('admin', 'admin@battlebits.com', admin_pass, 1, datetime.now().isoformat())
        )
    
    conn.commit()
    conn.close()

def create_user(username, email, password_hash, is_admin=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, email, password_hash, 1 if is_admin else 0, datetime.now().isoformat())
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_purchase(user_id, items_json, total_price, payment_method, status="Aprovado"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO purchases (user_id, items_json, total_price, payment_method, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, items_json, total_price, payment_method, status, datetime.now().isoformat())
    )
    conn.commit()
    purchase_id = cursor.lastrowid
    conn.close()
    return purchase_id

def get_user_purchases(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM purchases WHERE user_id = ? ORDER BY id DESC", (user_id,))
    purchases = cursor.fetchall()
    conn.close()
    return purchases
