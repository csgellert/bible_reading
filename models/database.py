import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

# Adatbázis típus meghatározása
USE_POSTGRES = Config.is_postgres()

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
    import sqlite3


def get_db_connection():
    """Adatbázis kapcsolat létrehozása"""
    if USE_POSTGRES:
        conn = psycopg2.connect(Config.DATABASE_URL)
        return conn
    else:
        # SQLite - biztosítjuk, hogy a data mappa létezik
        os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
        conn = sqlite3.connect(Config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def get_cursor(conn):
    """Cursor létrehozása az adatbázis típusnak megfelelően"""
    if USE_POSTGRES:
        return conn.cursor(cursor_factory=RealDictCursor)
    else:
        return conn.cursor()


def row_to_dict(row):
    """Row objektum dict-té alakítása"""
    if row is None:
        return None
    if USE_POSTGRES:
        return dict(row) if row else None
    else:
        return dict(row) if row else None


def placeholder(index=None):
    """SQL placeholder az adatbázis típusnak megfelelően"""
    if USE_POSTGRES:
        return '%s'
    else:
        return '?'


def placeholders(count):
    """Több placeholder generálása"""
    p = placeholder()
    return ', '.join([p] * count)

def init_db():
    """Adatbázis táblák létrehozása"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    
    if USE_POSTGRES:
        # PostgreSQL szintaxis
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reading_plans (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                plan_file TEXT NOT NULL,
                description TEXT,
                start_date DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # start_date mező hozzáadása ha nem létezik (PostgreSQL-ben külön kell kezelni)
        try:
            cursor.execute('''
                ALTER TABLE reading_plans ADD COLUMN IF NOT EXISTS start_date DATE DEFAULT CURRENT_DATE
            ''')
        except Exception:
            conn.rollback()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                plan_id INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES reading_plans (id),
                UNIQUE(name, plan_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id SERIAL PRIMARY KEY,
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS highlights (
                id SERIAL PRIMARY KEY,
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reading_log (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                plan_id INTEGER NOT NULL DEFAULT 1,
                date TEXT NOT NULL,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (plan_id) REFERENCES reading_plans (id),
                UNIQUE(user_id, plan_id, date)
            )
        ''')
        
        # Reakciók tábla (like/szívecske)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reactions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                reaction_type TEXT DEFAULT 'heart',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, target_type, target_id)
            )
        ''')
        
        # Válasz kommentek tábla
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comment_replies (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                parent_comment_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (parent_comment_id) REFERENCES comments (id) ON DELETE CASCADE
            )
        ''')
        
        # is_private mező hozzáadása a comments és highlights táblákhoz (ha nem létezik)
        try:
            cursor.execute('ALTER TABLE comments ADD COLUMN IF NOT EXISTS is_private BOOLEAN DEFAULT FALSE')
        except Exception:
            conn.rollback()
        try:
            cursor.execute('ALTER TABLE highlights ADD COLUMN IF NOT EXISTS is_private BOOLEAN DEFAULT FALSE')
        except Exception:
            conn.rollback()
    else:
        # SQLite szintaxis
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reading_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                plan_file TEXT NOT NULL,
                description TEXT,
                start_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # start_date mező hozzáadása ha nem létezik
        try:
            cursor.execute('ALTER TABLE reading_plans ADD COLUMN start_date TEXT')
        except:
            pass
        
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
        
        # Reakciók tábla (like/szívecske)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                reaction_type TEXT DEFAULT 'heart',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, target_type, target_id)
            )
        ''')
        
        # Válasz kommentek tábla
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comment_replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                parent_comment_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (parent_comment_id) REFERENCES comments (id) ON DELETE CASCADE
            )
        ''')
        
        # is_private mező hozzáadása a comments és highlights táblákhoz (ha nem létezik)
        try:
            cursor.execute('ALTER TABLE comments ADD COLUMN is_private INTEGER DEFAULT 0')
        except:
            pass
        try:
            cursor.execute('ALTER TABLE highlights ADD COLUMN is_private INTEGER DEFAULT 0')
        except:
            pass
    
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
    cursor = get_cursor(conn)
    
    cursor.execute('SELECT id FROM reading_plans LIMIT 1')
    if cursor.fetchone() is None:
        # Létrehozzuk az alapértelmezett tervet a régi jelszóval
        password_hash = generate_password_hash(Config.SITE_PASSWORD)
        p = placeholder()
        cursor.execute(f'''
            INSERT INTO reading_plans (name, password_hash, plan_file, description)
            VALUES ({p}, {p}, {p}, {p})
        ''', ('Bibliaolvasási Terv 2025', password_hash, 'reading_plan.json', 'Alapértelmezett éves bibliaolvasási terv'))
        conn.commit()
    
    conn.close()


def get_plan_by_password(password):
    """Olvasási terv lekérése jelszó alapján"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    cursor.execute('SELECT * FROM reading_plans')
    plans = cursor.fetchall()
    conn.close()
    
    for plan in plans:
        plan_dict = row_to_dict(plan) if not USE_POSTGRES else dict(plan)
        if check_password_hash(plan_dict['password_hash'], password):
            return plan_dict
    return None


def get_plan_by_id(plan_id):
    """Olvasási terv lekérése ID alapján"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    cursor.execute(f'SELECT * FROM reading_plans WHERE id = {p}', (plan_id,))
    plan = cursor.fetchone()
    conn.close()
    return row_to_dict(plan)


def get_all_plans():
    """Összes olvasási terv lekérése"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    cursor.execute('SELECT id, name, plan_file, description, created_at FROM reading_plans ORDER BY name')
    plans = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return plans


def create_plan(name, password, plan_file, description='', start_date=None):
    """Új olvasási terv létrehozása"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    password_hash = generate_password_hash(password)
    p = placeholder()
    
    # Alapértelmezett start_date az aktuális nap
    if start_date is None:
        start_date = datetime.now().strftime('%Y-%m-%d')
    
    if USE_POSTGRES:
        cursor.execute(f'''
            INSERT INTO reading_plans (name, password_hash, plan_file, description, start_date)
            VALUES ({p}, {p}, {p}, {p}, {p}) RETURNING id
        ''', (name, password_hash, plan_file, description, start_date))
        plan_id = cursor.fetchone()['id']
    else:
        cursor.execute(f'''
            INSERT INTO reading_plans (name, password_hash, plan_file, description, start_date)
            VALUES ({p}, {p}, {p}, {p}, {p})
        ''', (name, password_hash, plan_file, description, start_date))
        plan_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return plan_id


def update_plan_start_date(plan_id, start_date):
    """Olvasási terv kezdő dátumának módosítása"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    cursor.execute(f'UPDATE reading_plans SET start_date = {p} WHERE id = {p}', (start_date, plan_id))
    conn.commit()
    conn.close()


def update_plan_password(plan_id, new_password):
    """Olvasási terv jelszavának módosítása"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    password_hash = generate_password_hash(new_password)
    p = placeholder()
    cursor.execute(f'UPDATE reading_plans SET password_hash = {p} WHERE id = {p}', (password_hash, plan_id))
    conn.commit()
    conn.close()


def update_plan(plan_id, name=None, description=None):
    """Olvasási terv adatainak módosítása"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    if name is not None:
        cursor.execute(f'UPDATE reading_plans SET name = {p} WHERE id = {p}', (name, plan_id))
    if description is not None:
        cursor.execute(f'UPDATE reading_plans SET description = {p} WHERE id = {p}', (description, plan_id))
    
    conn.commit()
    conn.close()


def delete_plan(plan_id):
    """Olvasási terv törlése (és minden kapcsolódó adat)"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    # Töröljük a kapcsolódó adatokat
    cursor.execute(f'DELETE FROM reading_log WHERE plan_id = {p}', (plan_id,))
    cursor.execute(f'DELETE FROM highlights WHERE plan_id = {p}', (plan_id,))
    cursor.execute(f'DELETE FROM comments WHERE plan_id = {p}', (plan_id,))
    cursor.execute(f'DELETE FROM users WHERE plan_id = {p}', (plan_id,))
    cursor.execute(f'DELETE FROM reading_plans WHERE id = {p}', (plan_id,))
    conn.commit()
    conn.close()


# ==========================================
# Felhasználó műveletek
# ==========================================

def get_or_create_user(name, plan_id):
    """Felhasználó lekérése vagy létrehozása adott tervhez"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    # Próbáljuk lekérni a felhasználót az adott tervből
    cursor.execute(f'SELECT * FROM users WHERE name = {p} AND plan_id = {p}', (name, plan_id))
    user = cursor.fetchone()
    
    if user is None:
        # Ha nem létezik, hozzuk létre
        cursor.execute(f'INSERT INTO users (name, plan_id) VALUES ({p}, {p})', (name, plan_id))
        conn.commit()
        cursor.execute(f'SELECT * FROM users WHERE name = {p} AND plan_id = {p}', (name, plan_id))
        user = cursor.fetchone()
    
    conn.close()
    return row_to_dict(user)


def get_all_users(plan_id=None):
    """Összes felhasználó lekérése (opcionálisan terv szerint szűrve)"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    if plan_id:
        cursor.execute(f'SELECT * FROM users WHERE plan_id = {p} ORDER BY name', (plan_id,))
    else:
        cursor.execute('SELECT * FROM users ORDER BY name')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def delete_user(user_id, plan_id):
    """Felhasználó és minden kapcsolódó adatának törlése egy tervből"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    # Ellenőrizzük, hogy a felhasználó ehhez a tervhez tartozik-e
    cursor.execute(f'SELECT id FROM users WHERE id = {p} AND plan_id = {p}', (user_id, plan_id))
    if cursor.fetchone() is None:
        conn.close()
        return False
    
    # Töröljük a felhasználó adatait
    cursor.execute(f'DELETE FROM reading_log WHERE user_id = {p} AND plan_id = {p}', (user_id, plan_id))
    cursor.execute(f'DELETE FROM highlights WHERE user_id = {p} AND plan_id = {p}', (user_id, plan_id))
    cursor.execute(f'DELETE FROM comments WHERE user_id = {p} AND plan_id = {p}', (user_id, plan_id))
    cursor.execute(f'DELETE FROM users WHERE id = {p} AND plan_id = {p}', (user_id, plan_id))
    
    conn.commit()
    conn.close()
    return True


def get_user_stats(user_id, plan_id):
    """Felhasználó statisztikáinak lekérése"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    cursor.execute(f'SELECT COUNT(*) as cnt FROM comments WHERE user_id = {p} AND plan_id = {p}', (user_id, plan_id))
    comments_count = cursor.fetchone()['cnt']
    
    cursor.execute(f'SELECT COUNT(*) as cnt FROM highlights WHERE user_id = {p} AND plan_id = {p}', (user_id, plan_id))
    highlights_count = cursor.fetchone()['cnt']
    
    cursor.execute(f'SELECT COUNT(*) as cnt FROM reading_log WHERE user_id = {p} AND plan_id = {p}', (user_id, plan_id))
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
    cursor = get_cursor(conn)
    p = placeholder()
    
    if USE_POSTGRES:
        cursor.execute(f'''
            INSERT INTO comments (user_id, plan_id, date, verse_ref, content, comment_type)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p}) RETURNING id
        ''', (user_id, plan_id, date, verse_ref, content, comment_type))
        comment_id = cursor.fetchone()['id']
    else:
        cursor.execute(f'''
            INSERT INTO comments (user_id, plan_id, date, verse_ref, content, comment_type)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p})
        ''', (user_id, plan_id, date, verse_ref, content, comment_type))
        comment_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return comment_id

def get_comments_for_date(date, plan_id, current_user_id=None):
    """Adott nap kommentjeinek lekérése egy adott tervből (privát csak a tulajdonosnak látható)"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    if USE_POSTGRES:
        private_check = f"(c.is_private = FALSE OR c.is_private IS NULL OR c.user_id = {p})"
    else:
        private_check = f"(c.is_private = 0 OR c.is_private IS NULL OR c.user_id = {p})"
    
    cursor.execute(f'''
        SELECT c.*, u.name as user_name
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.date = {p} AND c.plan_id = {p} AND {private_check}
        ORDER BY c.created_at DESC
    ''', (date, plan_id, current_user_id or 0))
    comments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Reakciók és válaszok hozzáadása minden kommenthez
    for comment in comments:
        comment['reactions'] = get_reactions_for_target('comment', comment['id'])
        comment['reaction_count'] = len(comment['reactions'])
        comment['replies'] = get_replies_for_comment(comment['id'])
    
    return comments

def delete_comment(comment_id, user_id):
    """Komment törlése (csak a saját kommentet)"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    cursor.execute(f'DELETE FROM comments WHERE id = {p} AND user_id = {p}', (comment_id, user_id))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def update_comment(comment_id, user_id, content):
    """Komment szerkesztése (csak a saját kommentet)"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    cursor.execute(f'UPDATE comments SET content = {p} WHERE id = {p} AND user_id = {p}', (content, comment_id, user_id))
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


# ==========================================
# Kiemelés műveletek
# ==========================================

def add_highlight(user_id, plan_id, date, verse_ref, text, color='yellow'):
    """Új kiemelés hozzáadása"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    if USE_POSTGRES:
        cursor.execute(f'''
            INSERT INTO highlights (user_id, plan_id, date, verse_ref, text, color)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p}) RETURNING id
        ''', (user_id, plan_id, date, verse_ref, text, color))
        highlight_id = cursor.fetchone()['id']
    else:
        cursor.execute(f'''
            INSERT INTO highlights (user_id, plan_id, date, verse_ref, text, color)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p})
        ''', (user_id, plan_id, date, verse_ref, text, color))
        highlight_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return highlight_id

def get_highlights_for_date(date, plan_id, current_user_id=None):
    """Adott nap kiemelései egy adott tervből (privát csak a tulajdonosnak látható)"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    if USE_POSTGRES:
        private_check = f"(h.is_private = FALSE OR h.is_private IS NULL OR h.user_id = {p})"
    else:
        private_check = f"(h.is_private = 0 OR h.is_private IS NULL OR h.user_id = {p})"
    
    cursor.execute(f'''
        SELECT h.*, u.name as user_name
        FROM highlights h
        JOIN users u ON h.user_id = u.id
        WHERE h.date = {p} AND h.plan_id = {p} AND {private_check}
        ORDER BY h.created_at DESC
    ''', (date, plan_id, current_user_id or 0))
    highlights = [dict(row) for row in cursor.fetchall()]
    
    # Reakciók hozzáadása minden kiemeléshez (N+1 lekérdezés elkerülése érdekében batch-ben töltjük)
    highlight_ids = [h['id'] for h in highlights]
    reactions_by_highlight = {hid: [] for hid in highlight_ids}

    if highlight_ids:
        # Dinamikus IN lista a highlight azonosítókhoz
        in_placeholders = ', '.join([p] * len(highlight_ids))
        cursor.execute(
            f'''
            SELECT *
            FROM reactions
            WHERE target_type = {p}
              AND target_id IN ({in_placeholders})
            ''',
            tuple(['highlight'] + highlight_ids),
        )

        for row in cursor.fetchall():
            row_dict = dict(row)
            target_id = row_dict.get('target_id')
            if target_id in reactions_by_highlight:
                reactions_by_highlight[target_id].append(row_dict)

    # Reakciók és reakciószám beállítása a kiemelésekhez
    for highlight in highlights:
        hid = highlight['id']
        highlight_reactions = reactions_by_highlight.get(hid, [])
        highlight['reactions'] = highlight_reactions
        highlight['reaction_count'] = len(highlight_reactions)
    
    conn.close()
    return highlights

def delete_highlight(highlight_id, user_id):
    """Kiemelés törlése"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    cursor.execute(f'DELETE FROM highlights WHERE id = {p} AND user_id = {p}', (highlight_id, user_id))
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
    cursor = get_cursor(conn)
    p = placeholder()
    try:
        if USE_POSTGRES:
            cursor.execute(f'''
                INSERT INTO reading_log (user_id, plan_id, date)
                VALUES ({p}, {p}, {p})
                ON CONFLICT (user_id, plan_id, date) DO NOTHING
            ''', (user_id, plan_id, date))
        else:
            cursor.execute(f'''
                INSERT OR REPLACE INTO reading_log (user_id, plan_id, date)
                VALUES ({p}, {p}, {p})
            ''', (user_id, plan_id, date))
        conn.commit()
    except:
        pass
    conn.close()

def unmark_day_as_read(user_id, plan_id, date):
    """Olvasott megjelölés visszavonása"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    cursor.execute(f'DELETE FROM reading_log WHERE user_id = {p} AND plan_id = {p} AND date = {p}', (user_id, plan_id, date))
    conn.commit()
    conn.close()

def get_reading_log(user_id, plan_id):
    """Felhasználó olvasási naplója egy adott tervben"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    cursor.execute(f'SELECT date FROM reading_log WHERE user_id = {p} AND plan_id = {p}', (user_id, plan_id))
    dates = [row['date'] for row in cursor.fetchall()]
    conn.close()
    return dates

def get_all_reading_stats(plan_id):
    """Összes felhasználó olvasási statisztikája egy adott tervben"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    cursor.execute(f'''
        SELECT u.name, COUNT(r.id) as days_read
        FROM users u
        LEFT JOIN reading_log r ON u.id = r.user_id AND r.plan_id = {p}
        WHERE u.plan_id = {p}
        GROUP BY u.id, u.name
        ORDER BY days_read DESC
    ''', (plan_id, plan_id))
    stats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return stats

def get_readers_for_date(date, plan_id):
    """Adott nap olvasóinak lekérése egy adott tervből"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    cursor.execute(f'''
        SELECT u.name, r.completed_at
        FROM reading_log r
        JOIN users u ON r.user_id = u.id
        WHERE r.date = {p} AND r.plan_id = {p}
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
    cursor = get_cursor(conn)
    p = placeholder()
    query = f'''
        SELECT c.*, u.name as user_name
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.user_id = {p} AND c.plan_id = {p}
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
    cursor = get_cursor(conn)
    p = placeholder()
    query = f'''
        SELECT h.*, u.name as user_name
        FROM highlights h
        JOIN users u ON h.user_id = u.id
        WHERE h.user_id = {p} AND h.plan_id = {p}
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
    cursor = get_cursor(conn)
    p = placeholder()
    
    # Kombinált lekérdezés UNION-nal
    query = f'''
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
        WHERE c.user_id = {p} AND c.plan_id = {p}
        
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
        WHERE h.user_id = {p} AND h.plan_id = {p}
        
        ORDER BY created_at DESC
    '''
    if limit:
        query = query.replace('ORDER BY created_at DESC', f'ORDER BY created_at DESC LIMIT {limit}')
    
    cursor.execute(query, (user_id, plan_id, user_id, plan_id))
    notes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return notes


# ==========================================
# Reakciók (like/szívecske) műveletek
# ==========================================

def add_reaction(user_id, target_type, target_id, reaction_type='heart'):
    """Reakció hozzáadása"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    try:
        cursor.execute(f'''
            INSERT INTO reactions (user_id, target_type, target_id, reaction_type)
            VALUES ({p}, {p}, {p}, {p})
        ''', (user_id, target_type, target_id, reaction_type))
        conn.commit()
        
        # Visszaadjuk az új reakciók számát
        cursor.execute(f'''
            SELECT COUNT(*) as count FROM reactions
            WHERE target_type = {p} AND target_id = {p}
        ''', (target_type, target_id))
        result = cursor.fetchone()
        count = dict(result)['count'] if result else 0
        conn.close()
        return {'success': True, 'count': count}
    except Exception as e:
        conn.close()
        return {'success': False, 'error': str(e)}


def remove_reaction(user_id, target_type, target_id):
    """Reakció eltávolítása"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    cursor.execute(f'''
        DELETE FROM reactions
        WHERE user_id = {p} AND target_type = {p} AND target_id = {p}
    ''', (user_id, target_type, target_id))
    conn.commit()
    
    # Visszaadjuk az új reakciók számát
    cursor.execute(f'''
        SELECT COUNT(*) as count FROM reactions
        WHERE target_type = {p} AND target_id = {p}
    ''', (target_type, target_id))
    result = cursor.fetchone()
    count = dict(result)['count'] if result else 0
    conn.close()
    return count


def get_reactions_for_target(target_type, target_id):
    """Reakciók lekérése egy adott célhoz"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    cursor.execute(f'''
        SELECT r.*, u.name as user_name
        FROM reactions r
        JOIN users u ON r.user_id = u.id
        WHERE r.target_type = {p} AND r.target_id = {p}
    ''', (target_type, target_id))
    reactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return reactions


def has_user_reacted(user_id, target_type, target_id):
    """Ellenőrzi, hogy a felhasználó reagált-e már"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    cursor.execute(f'''
        SELECT id FROM reactions
        WHERE user_id = {p} AND target_type = {p} AND target_id = {p}
    ''', (user_id, target_type, target_id))
    result = cursor.fetchone()
    conn.close()
    return result is not None


# ==========================================
# Válasz kommentek műveletek
# ==========================================

def add_comment_reply(user_id, parent_comment_id, content):
    """Válasz hozzáadása egy kommenthez"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    if USE_POSTGRES:
        cursor.execute(f'''
            INSERT INTO comment_replies (user_id, parent_comment_id, content)
            VALUES ({p}, {p}, {p})
            RETURNING id
        ''', (user_id, parent_comment_id, content))
        reply_id = cursor.fetchone()['id']
    else:
        cursor.execute(f'''
            INSERT INTO comment_replies (user_id, parent_comment_id, content)
            VALUES ({p}, {p}, {p})
        ''', (user_id, parent_comment_id, content))
        reply_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return reply_id


def get_replies_for_comment(parent_comment_id):
    """Válaszok lekérése egy kommenthez"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    cursor.execute(f'''
        SELECT r.*, u.name as user_name
        FROM comment_replies r
        JOIN users u ON r.user_id = u.id
        WHERE r.parent_comment_id = {p}
        ORDER BY r.created_at ASC
    ''', (parent_comment_id,))
    replies = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return replies


def delete_comment_reply(reply_id, user_id):
    """Válasz törlése (csak a saját válaszok)"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    cursor.execute(f'''
        DELETE FROM comment_replies
        WHERE id = {p} AND user_id = {p}
    ''', (reply_id, user_id))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# ==========================================
# Privát jegyzet/kiemelés műveletek
# ==========================================

def update_comment_privacy(comment_id, user_id, is_private):
    """Komment privát státuszának módosítása"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    private_val = 1 if is_private else 0
    if USE_POSTGRES:
        private_val = is_private
    
    cursor.execute(f'''
        UPDATE comments
        SET is_private = {p}
        WHERE id = {p} AND user_id = {p}
    ''', (private_val, comment_id, user_id))
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def update_highlight_privacy(highlight_id, user_id, is_private):
    """Kiemelés privát státuszának módosítása"""
    conn = get_db_connection()
    cursor = get_cursor(conn)
    p = placeholder()
    
    private_val = 1 if is_private else 0
    if USE_POSTGRES:
        private_val = is_private
    
    cursor.execute(f'''
        UPDATE highlights
        SET is_private = {p}
        WHERE id = {p} AND user_id = {p}
    ''', (private_val, highlight_id, user_id))
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated
