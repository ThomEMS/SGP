# database.py
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_FILE = "depenses.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    # table depenses (si déjà présente, ne fait rien)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS depenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            montant REAL,
            categorie TEXT,
            description TEXT,
            type_depense TEXT,
            part_thomas REAL,
            part_autre REAL,
            nom_autre TEXT
        )
    ''')
    # table users
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            fullname TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Depenses
def ajouter_depense(montant, categorie, description, type_depense, part_thomas, part_autre, nom_autre):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO depenses (date, montant, categorie, description, type_depense, part_thomas, part_autre, nom_autre)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), montant, categorie, description, type_depense, part_thomas, part_autre, nom_autre))
    conn.commit()
    conn.close()

def get_resume():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
        SELECT categorie, type_depense, SUM(montant)
        FROM depenses
        GROUP BY categorie, type_depense
        ORDER BY categorie
    ''')
    data = cur.fetchall()
    conn.close()
    return data

# Users
def add_user(username, password, fullname=""):
    """Ajoute un utilisateur avec mot de passe hashé. Retourne True si ok, False si username existe."""
    password_hash = generate_password_hash(password)
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password_hash, fullname) VALUES (?, ?, ?)",
                    (username, password_hash, fullname))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def verify_user(username, password):
    """Retourne dict user si ok, sinon None."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash, fullname FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    user_id, usern, password_hash, fullname = row
    if check_password_hash(password_hash, password):
        return {"id": user_id, "username": usern, "fullname": fullname}
    return None
