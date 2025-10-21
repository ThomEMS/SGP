import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB_FILE = "budget.db"

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            net_income REAL NOT NULL,
            pay_frequency TEXT NOT NULL,
            next_pay_date TEXT,
            fixed_expenses REAL DEFAULT 0,
            savings_goal REAL DEFAULT 0,
            debt_payment REAL DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

def add_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    hash_pw = generate_password_hash(password)
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_pw))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

def verify_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row and check_password_hash(row[2], password):
        return {"id": row[0], "username": row[1]}
    return None
