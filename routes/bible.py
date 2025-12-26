from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from datetime import datetime, date
import json
import os
from config import Config
from models.database import (
    get_comments_for_date, add_comment, delete_comment,
    get_highlights_for_date, add_highlight, delete_highlight,
    mark_day_as_read, unmark_day_as_read, get_reading_log,
    get_all_users, get_all_reading_stats
)

bible_bp = Blueprint('bible', __name__)

def login_required(f):
    """Decorator: bejelentkezés szükséges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def load_reading_plan():
    """Olvasási terv betöltése JSON-ból"""
    try:
        with open(Config.READING_PLAN_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def get_today_string():
    """Mai dátum string formátumban (MM-DD)"""
    return datetime.now().strftime('%m-%d')

def get_date_string(date_str):
    """Dátum formázása megjelenítéshez"""
    try:
        month, day = date_str.split('-')
        months = ['január', 'február', 'március', 'április', 'május', 'június',
                  'július', 'augusztus', 'szeptember', 'október', 'november', 'december']
        return f"{months[int(month)-1]} {int(day)}."
    except:
        return date_str

@bible_bp.route('/')
@login_required
def index():
    """Főoldal - átirányítás a mai napra"""
    return redirect(url_for('bible.daily'))

@bible_bp.route('/daily')
@bible_bp.route('/daily/<date_str>')
@login_required
def daily(date_str=None):
    """Napi olvasmány oldal"""
    if date_str is None:
        date_str = get_today_string()
    
    # Olvasási terv betöltése
    reading_plan = load_reading_plan()
    
    # Mai szakaszok
    daily_readings = reading_plan.get(date_str, {})
    
    # Kommentek és kiemelések
    comments = get_comments_for_date(date_str)
    highlights = get_highlights_for_date(date_str)
    
    # Olvasási napló
    user_reading_log = get_reading_log(session['user_id'])
    is_read = date_str in user_reading_log
    
    # Előző és következő nap
    try:
        month, day = map(int, date_str.split('-'))
        current_date = date(2025, month, day)
        
        # Előző nap
        from datetime import timedelta
        prev_date = current_date - timedelta(days=1)
        next_date = current_date + timedelta(days=1)
        
        prev_str = prev_date.strftime('%m-%d')
        next_str = next_date.strftime('%m-%d')
    except:
        prev_str = None
        next_str = None
    
    return render_template('daily.html',
                         date_str=date_str,
                         date_display=get_date_string(date_str),
                         readings=daily_readings,
                         comments=comments,
                         highlights=highlights,
                         is_read=is_read,
                         prev_date=prev_str,
                         next_date=next_str,
                         today=get_today_string(),
                         users=get_all_users())

@bible_bp.route('/calendar')
@login_required
def calendar():
    """Éves naptár nézet"""
    reading_plan = load_reading_plan()
    user_reading_log = get_reading_log(session['user_id'])
    stats = get_all_reading_stats()
    
    # Hónapok létrehozása
    months = []
    month_names = ['Január', 'Február', 'Március', 'Április', 'Május', 'Június',
                   'Július', 'Augusztus', 'Szeptember', 'Október', 'November', 'December']
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    for m in range(12):
        month_data = {
            'name': month_names[m],
            'days': []
        }
        for d in range(1, days_in_month[m] + 1):
            date_str = f"{m+1:02d}-{d:02d}"
            has_reading = date_str in reading_plan
            is_read = date_str in user_reading_log
            is_today = date_str == get_today_string()
            
            month_data['days'].append({
                'day': d,
                'date_str': date_str,
                'has_reading': has_reading,
                'is_read': is_read,
                'is_today': is_today
            })
        months.append(month_data)
    
    return render_template('calendar.html',
                         months=months,
                         stats=stats,
                         total_read=len(user_reading_log))

# API végpontok
@bible_bp.route('/api/comment', methods=['POST'])
@login_required
def api_add_comment():
    """Komment hozzáadása"""
    data = request.get_json()
    date_str = data.get('date')
    content = data.get('content', '').strip()
    verse_ref = data.get('verse_ref', '')
    comment_type = data.get('type', 'comment')
    
    if not content:
        return jsonify({'error': 'Üres komment'}), 400
    
    comment_id = add_comment(
        user_id=session['user_id'],
        date=date_str,
        content=content,
        verse_ref=verse_ref,
        comment_type=comment_type
    )
    
    return jsonify({
        'success': True,
        'id': comment_id,
        'username': session['username']
    })

@bible_bp.route('/api/comment/<int:comment_id>', methods=['DELETE'])
@login_required
def api_delete_comment(comment_id):
    """Komment törlése"""
    deleted = delete_comment(comment_id, session['user_id'])
    return jsonify({'success': deleted})

@bible_bp.route('/api/highlight', methods=['POST'])
@login_required
def api_add_highlight():
    """Kiemelés hozzáadása"""
    data = request.get_json()
    date_str = data.get('date')
    verse_ref = data.get('verse_ref', '')
    text = data.get('text', '').strip()
    color = data.get('color', 'yellow')
    
    if not text:
        return jsonify({'error': 'Üres kiemelés'}), 400
    
    highlight_id = add_highlight(
        user_id=session['user_id'],
        date=date_str,
        verse_ref=verse_ref,
        text=text,
        color=color
    )
    
    return jsonify({
        'success': True,
        'id': highlight_id,
        'username': session['username']
    })

@bible_bp.route('/api/highlight/<int:highlight_id>', methods=['DELETE'])
@login_required
def api_delete_highlight(highlight_id):
    """Kiemelés törlése"""
    deleted = delete_highlight(highlight_id, session['user_id'])
    return jsonify({'success': deleted})

@bible_bp.route('/api/mark-read', methods=['POST'])
@login_required
def api_mark_read():
    """Nap megjelölése olvasottként"""
    data = request.get_json()
    date_str = data.get('date')
    is_read = data.get('is_read', True)
    
    if is_read:
        mark_day_as_read(session['user_id'], date_str)
    else:
        unmark_day_as_read(session['user_id'], date_str)
    
    return jsonify({'success': True})
