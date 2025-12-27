from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from functools import wraps
from datetime import datetime, date
import json
import os
from config import Config
from models.database import (
    get_comments_for_date, add_comment, delete_comment,
    get_highlights_for_date, add_highlight, delete_highlight,
    mark_day_as_read, unmark_day_as_read, get_reading_log,
    get_all_users, get_all_reading_stats, get_readers_for_date,
    get_user_comments, get_user_highlights, get_user_notes_combined,
    get_plan_by_id
)
from services.bible_api import fetch_verses_from_api, format_verses_html, get_available_translations

bible_bp = Blueprint('bible', __name__)

def login_required(f):
    """Decorator: bejelentkezés szükséges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def load_reading_plan(plan_id=None):
    """Olvasási terv betöltése JSON-ból (terv alapján)"""
    try:
        # Ha van plan_id, az adott terv fájlját töltjük be
        if plan_id:
            plan = get_plan_by_id(plan_id)
            if plan:
                plan_file = plan['plan_file']
                plan_path = os.path.join(os.path.dirname(Config.READING_PLAN_PATH), plan_file)
                if os.path.exists(plan_path):
                    with open(plan_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
        
        # Alapértelmezett terv fájl
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
    """Főoldal - terv leírása"""
    plan_id = session.get('plan_id')
    plan = get_plan_by_id(plan_id)
    
    # Olvasási statisztikák
    user_reading_log = get_reading_log(session['user_id'], plan_id)
    stats = get_all_reading_stats(plan_id)
    
    # Összes nap a tervben
    reading_plan = load_reading_plan(plan_id)
    total_days = len(reading_plan)
    
    return render_template('home.html',
                         plan=plan,
                         total_days=total_days,
                         days_read=len(user_reading_log),
                         stats=stats)

@bible_bp.route('/daily')
@bible_bp.route('/daily/<date_str>')
@login_required
def daily(date_str=None):
    """Napi olvasmány oldal"""
    if date_str is None:
        date_str = get_today_string()
    
    plan_id = session.get('plan_id')
    
    # Olvasási terv betöltése
    reading_plan = load_reading_plan(plan_id)
    
    # Mai szakaszok - átalakítás listává
    daily_readings_raw = reading_plan.get(date_str, {})
    
    # Szakasz típusok metaadatai
    section_types = {
        'ot': {'name': 'Ószövetség', 'icon': 'bi-bookmark', 'order': 1},
        'nt': {'name': 'Újszövetség', 'icon': 'bi-bookmark-fill', 'order': 2},
        'ps': {'name': 'Zsoltár', 'icon': 'bi-music-note', 'order': 3},
        'pr': {'name': 'Példabeszédek', 'icon': 'bi-lightbulb', 'order': 4},
    }
    
    # Lista formátum készítése
    readings_list = []
    
    # Ha a readings már lista formátumú (sections kulccsal)
    if 'sections' in daily_readings_raw:
        readings_list = daily_readings_raw['sections']
    else:
        # Régi formátum átalakítása (ot, nt, ps, pr kulcsok)
        for key in ['ot', 'nt', 'ps', 'pr']:
            if key in daily_readings_raw and daily_readings_raw[key]:
                meta = section_types.get(key, {'name': key.upper(), 'icon': 'bi-book', 'order': 99})
                readings_list.append({
                    'id': key,
                    'name': meta['name'],
                    'icon': meta['icon'],
                    'reference': daily_readings_raw[key],
                    'order': meta['order']
                })
        
        # Egyéb kulcsok (ami nem ot, nt, ps, pr)
        custom_order = 10
        for key, value in daily_readings_raw.items():
            if key not in ['ot', 'nt', 'ps', 'pr'] and value:
                readings_list.append({
                    'id': key,
                    'name': key,
                    'icon': 'bi-book',
                    'reference': value,
                    'order': custom_order
                })
                custom_order += 1
        
        # Rendezés order szerint
        readings_list.sort(key=lambda x: x.get('order', 99))
    
    # Kommentek és kiemelések
    comments = get_comments_for_date(date_str, plan_id)
    highlights = get_highlights_for_date(date_str, plan_id)
    
    # Olvasási napló
    user_reading_log = get_reading_log(session['user_id'], plan_id)
    is_read = date_str in user_reading_log
    
    # Kik olvasták már el ezt a napot
    readers = get_readers_for_date(date_str, plan_id)
    readers_count = len(readers)
    
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
                         readings=readings_list,
                         comments=comments,
                         highlights=highlights,
                         is_read=is_read,
                         readers=readers,
                         readers_count=readers_count,
                         prev_date=prev_str,
                         next_date=next_str,
                         today=get_today_string(),
                         users=get_all_users(plan_id))

@bible_bp.route('/calendar')
@login_required
def calendar():
    """Éves naptár nézet"""
    plan_id = session.get('plan_id')
    reading_plan = load_reading_plan(plan_id)
    user_reading_log = get_reading_log(session['user_id'], plan_id)
    stats = get_all_reading_stats(plan_id)
    
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
    
    plan_id = session.get('plan_id')
    
    comment_id = add_comment(
        user_id=session['user_id'],
        plan_id=plan_id,
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
    
    plan_id = session.get('plan_id')
    
    highlight_id = add_highlight(
        user_id=session['user_id'],
        plan_id=plan_id,
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
    
    plan_id = session.get('plan_id')
    
    if is_read:
        mark_day_as_read(session['user_id'], plan_id, date_str)
    else:
        unmark_day_as_read(session['user_id'], plan_id, date_str)
    
    return jsonify({'success': True})


@bible_bp.route('/api/verses/<path:reference>')
@login_required
def api_get_verses(reference):
    """
    Biblia versek lekérése API-ból vagy helyi adatbázisból.
    
    Példa: /api/verses/1Móz1-3 vagy /api/verses/Mt5:1-12
    Query paraméterek:
        - translation: Fordítás kódja (SZIT, RUF, KG, stb.)
    """
    bible_source = current_app.config.get('BIBLE_SOURCE', 'api')
    
    # Fordítás a query paraméterből vagy alapértelmezettből
    translation = request.args.get('translation', current_app.config.get('BIBLE_TRANSLATION', 'SZIT'))
    
    if bible_source == 'api':
        # szentiras.eu API használata
        result = fetch_verses_from_api(reference, translation)
        
        if result['success']:
            return jsonify({
                'success': True,
                'html': format_verses_html(result),
                'verses': result['verses'],
                'full_reference': result['full_reference'],
                'source': 'szentiras.eu',
                'translation': translation
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Ismeretlen hiba'),
                'html': f'<p class="text-muted"><i class="bi bi-info-circle"></i> {result.get("error", "Nem sikerült betölteni")}</p>',
                'reference': reference
            })
    else:
        # Helyi adatbázis (még nincs implementálva)
        return jsonify({
            'success': False,
            'error': 'Helyi adatbázis még nincs implementálva',
            'html': '<p class="text-muted"><i class="bi bi-info-circle"></i> Helyi adatbázis még nincs implementálva</p>',
            'reference': reference
        })


@bible_bp.route('/api/bible-source')
@login_required
def api_bible_source():
    """Visszaadja a jelenlegi biblia forrás beállításokat"""
    return jsonify({
        'source': current_app.config.get('BIBLE_SOURCE', 'api'),
        'translation': current_app.config.get('BIBLE_TRANSLATION', 'SZIT'),
        'api_url': current_app.config.get('BIBLE_API_URL', 'https://szentiras.eu/api')
    })


@bible_bp.route('/api/translations')
@login_required
def api_translations():
    """Visszaadja az elérhető fordítások listáját"""
    translations = get_available_translations()
    default_translation = current_app.config.get('BIBLE_TRANSLATION', 'SZIT')
    
    return jsonify({
        'translations': translations,
        'default': default_translation
    })


@bible_bp.route('/my-notes')
@login_required
def my_notes():
    """Saját jegyzetek és kiemelések oldal"""
    user_id = session.get('user_id')
    plan_id = session.get('plan_id')
    
    # Nézet típusa: 'all', 'comments', 'highlights'
    view_type = request.args.get('view', 'all')
    
    if view_type == 'comments':
        notes = get_user_comments(user_id, plan_id)
    elif view_type == 'highlights':
        notes = get_user_highlights(user_id, plan_id)
        # Átalakítjuk a highlights formátumot
        for note in notes:
            note['type'] = 'highlight'
    else:
        notes = get_user_notes_combined(user_id, plan_id)
    
    # Statisztikák
    total_comments = len(get_user_comments(user_id, plan_id))
    total_highlights = len(get_user_highlights(user_id, plan_id))
    
    return render_template('my_notes.html',
                         notes=notes,
                         view_type=view_type,
                         total_comments=total_comments,
                         total_highlights=total_highlights,
                         username=session.get('username'))
