import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
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
    
    # Olvasási tervek tábla
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reading_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            plan_file TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Felhasználók tábla - plan_id hozzáadva
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            plan_id INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES reading_plans (id),
            UNIQUE(name, plan_id)
        )
    ''')
    
    # Kommentek/gondolatok tábla - plan_id hozzáadva
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL DEFAULT 1,
            date TEXT NOT NULL,
            verse_ref TEXT,
            content TEXT NOT NULL,
            comment_type TEXT DEFAULT 'comment',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (plan_id) REFERENCES reading_plans (id)
        )
    ''')
    
    # Kiemelések tábla - plan_id hozzáadva
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS highlights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL DEFAULT 1,
            date TEXT NOT NULL,
            verse_ref TEXT NOT NULL,
            text TEXT NOT NULL,
            color TEXT DEFAULT 'yellow',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (plan_id) REFERENCES reading_plans (id)
        )
    ''')
    
    # Olvasási napló - plan_id hozzáadva
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reading_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL DEFAULT 1,
            date TEXT NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (plan_id) REFERENCES reading_plans (id),
            UNIQUE(user_id, plan_id, date)
        )
    ''')
    
    conn.commit()
    conn.close()
    
    # Alapértelmezett terv létrehozása ha nem létezik
    create_default_plan_if_not_exists()


# ==========================================
# Olvasási terv műveletek
# ==========================================

def create_default_plan_if_not_exists():
    """Alapértelmezett olvasási terv létrehozása"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM reading_plans LIMIT 1')
    if cursor.fetchone() is None:
        # Létrehozzuk az alapértelmezett tervet a régi jelszóval
        password_hash = generate_password_hash(Config.SITE_PASSWORD)
        cursor.execute('''
            INSERT INTO reading_plans (name, password_hash, plan_file, description)
            VALUES (?, ?, ?, ?)
        ''', ('Bibliaolvasási Terv 2025', password_hash, 'reading_plan.json', 'Alapértelmezett éves bibliaolvasási terv'))
        conn.commit()
    
    conn.close()


def get_plan_by_password(password):
    """Olvasási terv lekérése jelszó alapján"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reading_plans')
    plans = cursor.fetchall()
    conn.close()
    
    for plan in plans:
        if check_password_hash(plan['password_hash'], password):
            return dict(plan)
    return None


def get_plan_by_id(plan_id):
    """Olvasási terv lekérése ID alapján"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reading_plans WHERE id = ?', (plan_id,))
    plan = cursor.fetchone()
    conn.close()
    return dict(plan) if plan else None


def get_all_plans():
    """Összes olvasási terv lekérése"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, plan_file, description, created_at FROM reading_plans ORDER BY name')
    plans = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return plans


def create_plan(name, password, plan_file, description=''):
    """Új olvasási terv létrehozása"""
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    cursor.execute('''
        INSERT INTO reading_plans (name, password_hash, plan_file, description)
        VALUES (?, ?, ?, ?)
    ''', (name, password_hash, plan_file, description))
    conn.commit()
    plan_id = cursor.lastrowid
    conn.close()
    return plan_id


def update_plan_password(plan_id, new_password):
    """Olvasási terv jelszavának módosítása"""
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hash = generate_password_hash(new_password)
    cursor.execute('UPDATE reading_plans SET password_hash = ? WHERE id = ?', (password_hash, plan_id))
    conn.commit()
    conn.close()


def update_plan(plan_id, name=None, description=None):
    """Olvasási terv adatainak módosítása"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if name is not None:
        cursor.execute('UPDATE reading_plans SET name = ? WHERE id = ?', (name, plan_id))
    if description is not None:
        cursor.execute('UPDATE reading_plans SET description = ? WHERE id = ?', (description, plan_id))
    
    conn.commit()
    conn.close()


def delete_plan(plan_id):
    """Olvasási terv törlése (és minden kapcsolódó adat)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Töröljük a kapcsolódó adatokat
    cursor.execute('DELETE FROM reading_log WHERE plan_id = ?', (plan_id,))
    cursor.execute('DELETE FROM highlights WHERE plan_id = ?', (plan_id,))
    cursor.execute('DELETE FROM comments WHERE plan_id = ?', (plan_id,))
    cursor.execute('DELETE FROM users WHERE plan_id = ?', (plan_id,))
    cursor.execute('DELETE FROM reading_plans WHERE id = ?', (plan_id,))
    conn.commit()
    conn.close()


# ==========================================
# Felhasználó műveletek
# ==========================================

def get_or_create_user(name, plan_id):
    """Felhasználó lekérése vagy létrehozása adott tervhez"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Próbáljuk lekérni a felhasználót az adott tervből
    cursor.execute('SELECT * FROM users WHERE name = ? AND plan_id = ?', (name, plan_id))
    user = cursor.fetchone()
    
    if user is None:
        # Ha nem létezik, hozzuk létre
        cursor.execute('INSERT INTO users (name, plan_id) VALUES (?, ?)', (name, plan_id))
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE name = ? AND plan_id = ?', (name, plan_id))
        user = cursor.fetchone()
    
    conn.close()
    return dict(user)


def get_all_users(plan_id=None):
    """Összes felhasználó lekérése (opcionálisan terv szerint szűrve)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if plan_id:
        cursor.execute('SELECT * FROM users WHERE plan_id = ? ORDER BY name', (plan_id,))
    else:
        cursor.execute('SELECT * FROM users ORDER BY name')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def delete_user(user_id, plan_id):
    """Felhasználó és minden kapcsolódó adatának törlése egy tervből"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ellenőrizzük, hogy a felhasználó ehhez a tervhez tartozik-e
    cursor.execute('SELECT id FROM users WHERE id = ? AND plan_id = ?', (user_id, plan_id))
    if cursor.fetchone() is None:
        conn.close()
        return False
    
    # Töröljük a felhasználó adatait
    cursor.execute('DELETE FROM reading_log WHERE user_id = ? AND plan_id = ?', (user_id, plan_id))
    cursor.execute('DELETE FROM highlights WHERE user_id = ? AND plan_id = ?', (user_id, plan_id))
    cursor.execute('DELETE FROM comments WHERE user_id = ? AND plan_id = ?', (user_id, plan_id))
    cursor.execute('DELETE FROM users WHERE id = ? AND plan_id = ?', (user_id, plan_id))
    
    conn.commit()
    conn.close()
    return True


def get_user_stats(user_id, plan_id):
    """Felhasználó statisztikáinak lekérése"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as cnt FROM comments WHERE user_id = ? AND plan_id = ?', (user_id, plan_id))
    comments_count = cursor.fetchone()['cnt']
    
    cursor.execute('SELECT COUNT(*) as cnt FROM highlights WHERE user_id = ? AND plan_id = ?', (user_id, plan_id))
    highlights_count = cursor.fetchone()['cnt']
    
    cursor.execute('SELECT COUNT(*) as cnt FROM reading_log WHERE user_id = ? AND plan_id = ?', (user_id, plan_id))
    reading_count = cursor.fetchone()['cnt']
    
    conn.close()
    return {
        'comments': comments_count,
        'highlights': highlights_count,
        'days_read': reading_count
    }

# ==========================================
# Komment műveletek
# ==========================================

def add_comment(user_id, plan_id, date, content, verse_ref=None, comment_type='comment'):
    """Új komment hozzáadása"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO comments (user_id, plan_id, date, verse_ref, content, comment_type)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, plan_id, date, verse_ref, content, comment_type))
    conn.commit()
    comment_id = cursor.lastrowid
    conn.close()
    return comment_id

def get_comments_for_date(date, plan_id):
    """Adott nap kommentjeinek lekérése egy adott tervből"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, u.name as user_name
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.date = ? AND c.plan_id = ?
        ORDER BY c.created_at DESC
    ''', (date, plan_id))
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


# ==========================================
# Kiemelés műveletek
# ==========================================

def add_highlight(user_id, plan_id, date, verse_ref, text, color='yellow'):
    """Új kiemelés hozzáadása"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO highlights (user_id, plan_id, date, verse_ref, text, color)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, plan_id, date, verse_ref, text, color))
    conn.commit()
    highlight_id = cursor.lastrowid
    conn.close()
    return highlight_id

def get_highlights_for_date(date, plan_id):
    """Adott nap kiemelései egy adott tervből"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT h.*, u.name as user_name
        FROM highlights h
        JOIN users u ON h.user_id = u.id
        WHERE h.date = ? AND h.plan_id = ?
        ORDER BY h.created_at DESC
    ''', (date, plan_id))
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


# ==========================================
# Olvasási napló műveletek
# ==========================================

def mark_day_as_read(user_id, plan_id, date):
    """Nap megjelölése olvasottként"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO reading_log (user_id, plan_id, date)
            VALUES (?, ?, ?)
        ''', (user_id, plan_id, date))
        conn.commit()
    except:
        pass
    conn.close()

def unmark_day_as_read(user_id, plan_id, date):
    """Olvasott megjelölés visszavonása"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM reading_log WHERE user_id = ? AND plan_id = ? AND date = ?', (user_id, plan_id, date))
    conn.commit()
    conn.close()

def get_reading_log(user_id, plan_id):
    """Felhasználó olvasási naplója egy adott tervben"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT date FROM reading_log WHERE user_id = ? AND plan_id = ?', (user_id, plan_id))
    dates = [row['date'] for row in cursor.fetchall()]
    conn.close()
    return dates

def get_all_reading_stats(plan_id):
    """Összes felhasználó olvasási statisztikája egy adott tervben"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.name, COUNT(r.id) as days_read
        FROM users u
        LEFT JOIN reading_log r ON u.id = r.user_id AND r.plan_id = ?
        WHERE u.plan_id = ?
        GROUP BY u.id
        ORDER BY days_read DESC
    ''', (plan_id, plan_id))
    stats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return stats

def get_readers_for_date(date, plan_id):
    """Adott nap olvasóinak lekérése egy adott tervből"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.name, r.completed_at
        FROM reading_log r
        JOIN users u ON r.user_id = u.id
        WHERE r.date = ? AND r.plan_id = ?
        ORDER BY r.completed_at DESC
    ''', (date, plan_id))
    readers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return readers


# ==========================================
# Felhasználói jegyzetek összesítés
# ==========================================

def get_user_comments(user_id, plan_id, limit=None):
    """Felhasználó összes kommentjének lekérése időrendben visszafelé"""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = '''
        SELECT c.*, u.name as user_name
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.user_id = ? AND c.plan_id = ?
        ORDER BY c.created_at DESC
    '''
    if limit:
        query += f' LIMIT {limit}'
    cursor.execute(query, (user_id, plan_id))
    comments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return comments


def get_user_highlights(user_id, plan_id, limit=None):
    """Felhasználó összes kiemelésének lekérése időrendben visszafelé"""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = '''
        SELECT h.*, u.name as user_name
        FROM highlights h
        JOIN users u ON h.user_id = u.id
        WHERE h.user_id = ? AND h.plan_id = ?
        ORDER BY h.created_at DESC
    '''
    if limit:
        query += f' LIMIT {limit}'
    cursor.execute(query, (user_id, plan_id))
    highlights = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return highlights


def get_user_notes_combined(user_id, plan_id, limit=None):
    """Felhasználó összes jegyzetének és kiemelésének lekérése együtt, időrendben visszafelé"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Kombinált lekérdezés UNION-nal
    query = '''
        SELECT 
            'comment' as type,
            c.id,
            c.date,
            c.verse_ref,
            c.content as text,
            c.comment_type,
            NULL as color,
            c.created_at
        FROM comments c
        WHERE c.user_id = ? AND c.plan_id = ?
        
        UNION ALL
        
        SELECT 
            'highlight' as type,
            h.id,
            h.date,
            h.verse_ref,
            h.text,
            NULL as comment_type,
            h.color,
            h.created_at
        FROM highlights h
        WHERE h.user_id = ? AND h.plan_id = ?
        
        ORDER BY created_at DESC
    '''
    if limit:
        query = query.replace('ORDER BY created_at DESC', f'ORDER BY created_at DESC LIMIT {limit}')
    
    cursor.execute(query, (user_id, plan_id, user_id, plan_id))
    notes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return notes
