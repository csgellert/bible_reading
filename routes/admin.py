from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from datetime import datetime, date
from models.database import (
    get_all_plans, create_plan, delete_plan, update_plan_password, update_plan,
    get_plan_by_id, get_all_users, delete_user, get_user_stats,
    update_plan_start_date
)
from config import Config
import os
import json
import re

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin jelszó a .env fájlból
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin2025')

def admin_required(f):
    """Decorator: admin jogosultság szükséges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Admin jogosultság szükséges!', 'error')
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    """Admin bejelentkezési oldal"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            flash('Sikeres admin bejelentkezés!', 'success')
            return redirect(url_for('admin.plans'))
        else:
            flash('Hibás admin jelszó!', 'error')
    
    return render_template('admin/login.html')


@admin_bp.route('/logout')
def admin_logout():
    """Admin kijelentkezés"""
    session.pop('is_admin', None)
    flash('Admin kijelentkezés sikeres!', 'success')
    return redirect(url_for('auth.login'))


@admin_bp.route('/plans')
@admin_required
def plans():
    """Olvasási tervek kezelése"""
    all_plans = get_all_plans()
    
    # Hozzáadjuk a felhasználók számát
    for plan in all_plans:
        users = get_all_users(plan['id'])
        plan['user_count'] = len(users)
    
    return render_template('admin/plans.html', plans=all_plans)


@admin_bp.route('/plans/create', methods=['GET', 'POST'])
@admin_required
def create_plan_view():
    """Új olvasási terv létrehozása"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '').strip()
        plan_file = request.form.get('plan_file', 'reading_plan.json').strip()
        description = request.form.get('description', '').strip()
        start_date = request.form.get('start_date', '').strip()
        
        if not name or not password:
            flash('A név és jelszó megadása kötelező!', 'error')
            return render_template('admin/create_plan.html')
        
        # Kezdő dátum validálása
        if start_date:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                flash('Érvénytelen dátum formátum! Használd: ÉÉÉÉ-HH-NN', 'error')
                return render_template('admin/create_plan.html')
        else:
            start_date = date.today().strftime('%Y-%m-%d')
        
        # Terv létrehozása
        plan_id = create_plan(name, password, plan_file, description, start_date)
        flash(f'Olvasási terv létrehozva: {name}', 'success')
        return redirect(url_for('admin.plans'))
    
    # Elérhető terv fájlok listázása
    data_dir = os.path.dirname(Config.READING_PLAN_PATH)
    plan_files = []
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            # Minden JSON fájl megjelenítése, kivéve a technikai fájlokat
            if f.endswith('.json') and not f.startswith('.'):
                plan_files.append(f)
    
    if not plan_files:
        plan_files = ['reading_plan.json']
    
    return render_template('admin/create_plan.html', plan_files=plan_files)


@admin_bp.route('/plans/<int:plan_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_plan(plan_id):
    """Olvasási terv szerkesztése"""
    plan = get_plan_by_id(plan_id)
    if not plan:
        flash('Terv nem található!', 'error')
        return redirect(url_for('admin.plans'))
    
    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        new_name = request.form.get('name', '').strip()
        new_description = request.form.get('description', '').strip()
        new_start_date = request.form.get('start_date', '').strip()
        
        if new_password:
            update_plan_password(plan_id, new_password)
            flash('Jelszó módosítva!', 'success')
        
        if new_name or new_description is not None:
            update_plan(plan_id, 
                       name=new_name if new_name else None,
                       description=new_description)
            flash('Terv adatai módosítva!', 'success')
        
        if new_start_date:
            try:
                datetime.strptime(new_start_date, '%Y-%m-%d')
                update_plan_start_date(plan_id, new_start_date)
                flash('Kezdő dátum módosítva!', 'success')
            except ValueError:
                flash('Érvénytelen dátum formátum!', 'error')
        
        return redirect(url_for('admin.edit_plan', plan_id=plan_id))
    
    users = get_all_users(plan_id)
    
    # Hozzáadjuk a statisztikákat minden felhasználóhoz
    for user in users:
        user['stats'] = get_user_stats(user['id'], plan_id)
    
    return render_template('admin/edit_plan.html', plan=plan, users=users)


@admin_bp.route('/plans/<int:plan_id>/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user_view(plan_id, user_id):
    """Felhasználó törlése egy tervből"""
    plan = get_plan_by_id(plan_id)
    if not plan:
        flash('Terv nem található!', 'error')
        return redirect(url_for('admin.plans'))
    
    deleted = delete_user(user_id, plan_id)
    if deleted:
        flash('Felhasználó törölve!', 'success')
    else:
        flash('Felhasználó nem található!', 'error')
    
    return redirect(url_for('admin.edit_plan', plan_id=plan_id))


@admin_bp.route('/plans/<int:plan_id>/delete', methods=['POST'])
@admin_required
def delete_plan_view(plan_id):
    """Olvasási terv törlése"""
    plan = get_plan_by_id(plan_id)
    if not plan:
        flash('Terv nem található!', 'error')
        return redirect(url_for('admin.plans'))
    
    # Ne engedjük törölni az utolsó tervet
    all_plans = get_all_plans()
    if len(all_plans) <= 1:
        flash('Az utolsó tervet nem lehet törölni!', 'error')
        return redirect(url_for('admin.plans'))
    
    delete_plan(plan_id)
    flash(f'Terv törölve: {plan["name"]}', 'success')
    return redirect(url_for('admin.plans'))


# ===========================================
# Olvasási terv tartalom szerkesztése
# ===========================================

def validate_plan_file(plan_file):
    """
    Validate plan_file to prevent path traversal attacks.
    Only allows filenames with alphanumeric characters, underscores, hyphens, and .json extension.
    """
    if not plan_file:
        raise ValueError("Plan file name cannot be empty")
    
    # Check for path traversal sequences
    if '..' in plan_file or '/' in plan_file or '\\' in plan_file:
        raise ValueError("Invalid plan file name: path traversal characters detected")
    
    # Only allow safe characters: alphanumeric, underscore, hyphen, and .json extension
    # Filename must start with alphanumeric character to avoid command-line option confusion
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*\.json$', plan_file):
        raise ValueError("Invalid plan file name: must start with alphanumeric character and contain only alphanumeric characters, underscores, hyphens, and .json extension")
    
    return True

def load_plan_file(plan_file):
    """Olvasási terv fájl betöltése"""
    validate_plan_file(plan_file)
    plan_path = os.path.join(os.path.dirname(Config.READING_PLAN_PATH), plan_file)
    if os.path.exists(plan_path):
        with open(plan_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_plan_file(plan_file, data):
    """Olvasási terv fájl mentése"""
    validate_plan_file(plan_file)
    plan_path = os.path.join(os.path.dirname(Config.READING_PLAN_PATH), plan_file)
    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


@admin_bp.route('/plans/<int:plan_id>/readings')
@admin_required
def edit_readings(plan_id):
    """Olvasási terv tartalom szerkesztése"""
    plan = get_plan_by_id(plan_id)
    if not plan:
        flash('Terv nem található!', 'error')
        return redirect(url_for('admin.plans'))
    
    plan_data = load_plan_file(plan['plan_file'])
    
    # Rendezés: ha számozott (1, 2, 3...), akkor szám szerint, egyébként string szerint
    sorted_keys = sorted(
        plan_data.keys(),
        key=lambda x: (0, int(str(x))) if str(x).isdigit() else (1, str(x))
    )
    
    readings = []
    for key in sorted_keys:
        readings.append({
            'day': key,
            'data': plan_data[key]
        })
    
    # Ellenőrizzük, hogy számozott-e a terv
    is_numbered = len(plan_data) > 0 and list(plan_data.keys())[0].isdigit()
    
    return render_template('admin/edit_readings.html', 
                          plan=plan, 
                          readings=readings,
                          is_numbered=is_numbered)


@admin_bp.route('/plans/<int:plan_id>/readings/<day>', methods=['GET', 'POST'])
@admin_required
def edit_reading_day(plan_id, day):
    """Egy adott nap olvasmányainak szerkesztése"""
    plan = get_plan_by_id(plan_id)
    if not plan:
        flash('Terv nem található!', 'error')
        return redirect(url_for('admin.plans'))
    
    plan_data = load_plan_file(plan['plan_file'])
    
    if request.method == 'POST':
        # Mentés
        ot = request.form.get('ot', '').strip()
        nt = request.form.get('nt', '').strip()
        ps = request.form.get('ps', '').strip()
        pr = request.form.get('pr', '').strip()
        
        day_data = {}
        if ot:
            day_data['ot'] = ot
        if nt:
            day_data['nt'] = nt
        if ps:
            day_data['ps'] = ps
        if pr:
            day_data['pr'] = pr
        
        if day_data:
            plan_data[day] = day_data
        elif day in plan_data:
            del plan_data[day]
        
        save_plan_file(plan['plan_file'], plan_data)
        flash(f'{day}. nap mentve!', 'success')
        return redirect(url_for('admin.edit_readings', plan_id=plan_id))
    
    # GET: nap adatainak betöltése
    day_data = plan_data.get(day, {})
    
    return render_template('admin/edit_reading_day.html',
                          plan=plan,
                          day=day,
                          day_data=day_data)


@admin_bp.route('/plans/<int:plan_id>/readings/add', methods=['GET', 'POST'])
@admin_required
def add_reading_day(plan_id):
    """Új nap hozzáadása az olvasási tervhez"""
    plan = get_plan_by_id(plan_id)
    if not plan:
        flash('Terv nem található!', 'error')
        return redirect(url_for('admin.plans'))
    
    plan_data = load_plan_file(plan['plan_file'])
    
    if request.method == 'POST':
        day = request.form.get('day', '').strip()
        ot = request.form.get('ot', '').strip()
        nt = request.form.get('nt', '').strip()
        ps = request.form.get('ps', '').strip()
        pr = request.form.get('pr', '').strip()
        
        if not day:
            flash('A nap megadása kötelező!', 'error')
            return render_template('admin/add_reading_day.html', plan=plan)
        
        if day in plan_data:
            flash(f'A {day}. nap már létezik! Használd a szerkesztést.', 'error')
            return render_template('admin/add_reading_day.html', plan=plan)
        
        day_data = {}
        if ot:
            day_data['ot'] = ot
        if nt:
            day_data['nt'] = nt
        if ps:
            day_data['ps'] = ps
        if pr:
            day_data['pr'] = pr
        
        if day_data:
            plan_data[day] = day_data
            save_plan_file(plan['plan_file'], plan_data)
            flash(f'{day}. nap hozzáadva!', 'success')
        else:
            flash('Legalább egy olvasmányt adj meg!', 'error')
            return render_template('admin/add_reading_day.html', plan=plan)
        
        return redirect(url_for('admin.edit_readings', plan_id=plan_id))
    
    # Következő nap javaslata
    if plan_data:
        try:
            max_day = max(int(k) for k in plan_data.keys() if k.isdigit())
            suggested_day = str(max_day + 1)
        except:
            suggested_day = ''
    else:
        suggested_day = '1'
    
    return render_template('admin/add_reading_day.html', plan=plan, suggested_day=suggested_day)


@admin_bp.route('/plans/<int:plan_id>/readings/<day>/delete', methods=['POST'])
@admin_required
def delete_reading_day(plan_id, day):
    """Nap törlése az olvasási tervből"""
    plan = get_plan_by_id(plan_id)
    if not plan:
        flash('Terv nem található!', 'error')
        return redirect(url_for('admin.plans'))
    
    plan_data = load_plan_file(plan['plan_file'])
    
    if day in plan_data:
        del plan_data[day]
        save_plan_file(plan['plan_file'], plan_data)
        flash(f'{day}. nap törölve!', 'success')
    else:
        flash('A nap nem található!', 'error')
    
    return redirect(url_for('admin.edit_readings', plan_id=plan_id))

