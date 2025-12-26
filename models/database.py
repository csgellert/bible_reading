import sqlite3
import os
from datetime import datetime
from config import Config

def get_db_connection():
    """Adatbázis kapcsolat létrehozása"""
    # Biztosítjuk, hogy a data mappa létezik
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Adatbázis táblák létrehozása"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Felhasználók tábla
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Kommentek/gondolatok tábla
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            verse_ref TEXT,
            content TEXT NOT NULL,
            comment_type TEXT DEFAULT 'comment',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Kiemelések tábla
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS highlights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            verse_ref TEXT NOT NULL,
            text TEXT NOT NULL,
            color TEXT DEFAULT 'yellow',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Olvasási napló - ki melyik napot olvasta el
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reading_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, date)
        )
    ''')
    
    conn.commit()
    conn.close()

# Felhasználó műveletek
def get_or_create_user(name):
    """Felhasználó lekérése vagy létrehozása"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Próbáljuk lekérni a felhasználót
    cursor.execute('SELECT * FROM users WHERE name = ?', (name,))
    user = cursor.fetchone()
    
    if user is None:
        # Ha nem létezik, hozzuk létre
        cursor.execute('INSERT INTO users (name) VALUES (?)', (name,))
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE name = ?', (name,))
        user = cursor.fetchone()
    
    conn.close()
    return dict(user)

def get_all_users():
    """Összes felhasználó lekérése"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY name')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

# Komment műveletek
def add_comment(user_id, date, content, verse_ref=None, comment_type='comment'):
    """Új komment hozzáadása"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO comments (user_id, date, verse_ref, content, comment_type)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, date, verse_ref, content, comment_type))
    conn.commit()
    comment_id = cursor.lastrowid
    conn.close()
    return comment_id

def get_comments_for_date(date):
    """Adott nap kommentjeinek lekérése"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, u.name as user_name
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.date = ?
        ORDER BY c.created_at DESC
    ''', (date,))
    comments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return comments

def delete_comment(comment_id, user_id):
    """Komment törlése (csak a saját kommentet)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM comments WHERE id = ? AND user_id = ?', (comment_id, user_id))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

# Kiemelés műveletek
def add_highlight(user_id, date, verse_ref, text, color='yellow'):
    """Új kiemelés hozzáadása"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO highlights (user_id, date, verse_ref, text, color)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, date, verse_ref, text, color))
    conn.commit()
    highlight_id = cursor.lastrowid
    conn.close()
    return highlight_id

def get_highlights_for_date(date):
    """Adott nap kiemelései"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT h.*, u.name as user_name
        FROM highlights h
        JOIN users u ON h.user_id = u.id
        WHERE h.date = ?
        ORDER BY h.created_at DESC
    ''', (date,))
    highlights = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return highlights

def delete_highlight(highlight_id, user_id):
    """Kiemelés törlése"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM highlights WHERE id = ? AND user_id = ?', (highlight_id, user_id))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

# Olvasási napló műveletek
def mark_day_as_read(user_id, date):
    """Nap megjelölése olvasottként"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO reading_log (user_id, date)
            VALUES (?, ?)
        ''', (user_id, date))
        conn.commit()
    except:
        pass
    conn.close()

def unmark_day_as_read(user_id, date):
    """Olvasott megjelölés visszavonása"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM reading_log WHERE user_id = ? AND date = ?', (user_id, date))
    conn.commit()
    conn.close()

def get_reading_log(user_id):
    """Felhasználó olvasási naplója"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT date FROM reading_log WHERE user_id = ?', (user_id,))
    dates = [row['date'] for row in cursor.fetchall()]
    conn.close()
    return dates

def get_all_reading_stats():
    """Összes felhasználó olvasási statisztikája"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.name, COUNT(r.id) as days_read
        FROM users u
        LEFT JOIN reading_log r ON u.id = r.user_id
        GROUP BY u.id
        ORDER BY days_read DESC
    ''')
    stats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return stats
