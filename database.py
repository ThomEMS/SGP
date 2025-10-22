import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "database.db")

def get_db_connection():
    """Create and return a SQLite connection with row access by name."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize all required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
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
    """Add a new user with hashed password."""
    conn = get_db_connection()
    cursor = conn.cursor()
    hash_pw = generate_password_hash(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hash_pw)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()


def verify_user(username, password):
    """Verify username and password, return user dict if valid."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash FROM users WHERE username=?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row and check_password_hash(row["password_hash"], password):
        return {"id": row["id"], "username": row["username"]}
    return None
