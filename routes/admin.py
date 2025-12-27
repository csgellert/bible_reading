from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from models.database import (
    get_all_plans, create_plan, delete_plan, update_plan_password, update_plan,
    get_plan_by_id, get_all_users, delete_user, get_user_stats
)
import os

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
        
        if not name or not password:
            flash('A név és jelszó megadása kötelező!', 'error')
            return render_template('admin/create_plan.html')
        
        # Terv létrehozása
        plan_id = create_plan(name, password, plan_file, description)
        flash(f'Olvasási terv létrehozva: {name}', 'success')
        return redirect(url_for('admin.plans'))
    
    # Elérhető terv fájlok listázása
    data_dir = os.path.dirname(Config.READING_PLAN_PATH)
    plan_files = []
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            if f.endswith('.json') and 'plan' in f.lower():
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
        
        if new_password:
            update_plan_password(plan_id, new_password)
            flash('Jelszó módosítva!', 'success')
        
        if new_name or new_description is not None:
            update_plan(plan_id, 
                       name=new_name if new_name else None,
                       description=new_description)
            flash('Terv adatai módosítva!', 'success')
        
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
