from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from config import Config
from models.database import get_or_create_user, get_plan_by_password, get_plan_by_id, get_all_users

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Bejelentkezési oldal"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        username = request.form.get('username', '').strip()
        
        # Jelszó alapján keressük meg a tervet
        plan = get_plan_by_password(password)
        if plan is None:
            flash('Hibás jelszó!', 'error')
            return render_template('login.html', username=username)
        
        # Felhasználónév ellenőrzése
        if not username or len(username) < 2:
            flash('Kérlek adj meg egy nevet (min. 2 karakter)!', 'error')
            return render_template('login.html', username=username)
        
        # Felhasználó létrehozása/lekérése az adott tervhez
        user = get_or_create_user(username, plan['id'])
        
        # Session beállítása
        session['authenticated'] = True
        session['user_id'] = user['id']
        session['username'] = user['name']
        session['plan_id'] = plan['id']
        session['plan_name'] = plan['name']
        session.permanent = True  # 31 napos session
        
        flash(f'Üdvözöllek, {username}! ({plan["name"]})', 'success')
        return redirect(url_for('bible.daily'))
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """Kijelentkezés"""
    session.clear()
    flash('Sikeres kijelentkezés!', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/switch-user', methods=['POST'])
def switch_user():
    """Felhasználóváltás (jelszó nélkül, ha már be van jelentkezve)"""
    if not session.get('authenticated'):
        return redirect(url_for('auth.login'))
    
    username = request.form.get('username', '').strip()
    plan_id = session.get('plan_id')
    
    if username and len(username) >= 2 and plan_id:
        user = get_or_create_user(username, plan_id)
        session['user_id'] = user['id']
        session['username'] = user['name']
        flash(f'Átváltottál: {username}', 'success')
    
    return redirect(url_for('bible.daily'))
