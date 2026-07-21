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
    
    # Tabela de usuários
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
    
    # Tabela de compras
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
    
    # Tabela de produtos (opcional – para catálogo)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            icon TEXT,
            description TEXT,
            duration TEXT,
            features TEXT,
            destaque BOOLEAN DEFAULT 0
        )
    ''')
    
    # Colunas extras de pagamento (adicionadas depois - protegido para bancos já existentes)
    for coluna, tipo in [
        ('preference_id', 'TEXT'),
        ('payment_id', 'TEXT'),
        ('buyer_email', 'TEXT'),
    ]:
        try:
            cursor.execute(f'ALTER TABLE purchases ADD COLUMN {coluna} {tipo}')
        except sqlite3.OperationalError:
            pass  # coluna já existe

    # Insere produtos padrão (se não existirem)
    default_products = [
        ('vip_master', 'VIP MASTER', 69.90, 'vip', 'ranks', 'fa-crown', 'Todos os benefícios exclusivos', 'Mensal', '["/fly", "/god", "10 homes"]', 1),
        ('vip_premium', 'VIP PREMIUM', 39.90, 'vip', 'ranks', 'fa-gem', 'Poderes e vantagens intermediárias', 'Mensal', '["/fly", "5 homes"]', 0),
        ('vip_basico', 'VIP BÁSICO', 19.90, 'vip', 'ranks', 'fa-star', 'Kit inicial com benefícios essenciais', 'Mensal', '["2 homes", "/fly"]', 0),
        ('clantag_battle', 'ClanTag Battle', 19.99, 'clantag', 'clantag', 'fa-tag', 'Tag exclusiva para seu clã', 'Permanente', '["Tag colorida", "Destaque no chat"]', 0),
        ('medalha_ouro', 'Medalha de Ouro', 19.99, 'medalha', 'medalhas', 'fa-medal', 'Medalha dourada de reconhecimento', 'Permanente', '["Ícone exclusivo", "Destaque no perfil"]', 0)
    ]
    
    for prod in default_products:
        cursor.execute('''
            INSERT OR IGNORE INTO products (id, name, price, type, category, icon, description, duration, features, destaque)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', prod)
    
    # Cria admin padrão
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

# ========== FUNÇÕES EXISTENTES ==========
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

def create_purchase(user_id, items_json, total_price, payment_method, status="pending", preference_id=None, buyer_email=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO purchases
           (user_id, items_json, total_price, payment_method, status, created_at, preference_id, buyer_email)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, items_json, total_price, payment_method, status, datetime.now().isoformat(), preference_id, buyer_email)
    )
    conn.commit()
    purchase_id = cursor.lastrowid
    conn.close()
    return purchase_id


def set_purchase_preference(purchase_id, preference_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE purchases SET preference_id = ? WHERE id = ?", (preference_id, purchase_id))
    conn.commit()
    conn.close()


def update_purchase_status(purchase_id, status, payment_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if payment_id:
        cursor.execute("UPDATE purchases SET status = ?, payment_id = ? WHERE id = ?", (status, payment_id, purchase_id))
    else:
        cursor.execute("UPDATE purchases SET status = ? WHERE id = ?", (status, purchase_id))
    conn.commit()
    conn.close()


def get_purchase_by_id(purchase_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,))
    purchase = cursor.fetchone()
    conn.close()
    return purchase

def get_user_purchases(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM purchases WHERE user_id = ? ORDER BY id DESC", (user_id,))
    purchases = cursor.fetchall()
    conn.close()
    return purchases

# ========== NOVAS FUNÇÕES PARA PRODUTOS (opcional) ==========
def get_all_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY price ASC")
    products = cursor.fetchall()
    conn.close()
    return products

def get_product_by_id(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()
    return product

def get_products_by_category(category):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE category = ? ORDER BY price ASC", (category,))
    products = cursor.fetchall()
    conn.close()
    return products