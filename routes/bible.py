from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from functools import wraps
from datetime import datetime, date, timedelta
import json
import os
from config import Config
from models.database import (
    get_comments_for_date, add_comment, delete_comment, update_comment,
    get_highlights_for_date, add_highlight, delete_highlight,
    mark_day_as_read, unmark_day_as_read, get_reading_log,
    get_all_users, get_all_reading_stats, get_readers_for_date,
    get_user_comments, get_user_highlights, get_user_notes_combined,
    get_plan_by_id,
    add_reaction, remove_reaction, has_user_reacted,
    add_comment_reply, get_replies_for_comment, delete_comment_reply,
    update_comment_privacy, update_highlight_privacy,
    get_reactions_for_target
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


def get_plan_start_date(plan_id):
    """Olvasási terv kezdő dátumának lekérése"""
    plan = get_plan_by_id(plan_id)
    if plan and plan.get('start_date'):
        start_date = plan['start_date']
        if isinstance(start_date, str):
            try:
                return datetime.strptime(start_date, '%Y-%m-%d').date()
            except:
                pass
        elif isinstance(start_date, date):
            return start_date
    # Alapértelmezett: Config-ból
    return Config.get_plan_start_date()


def get_day_number(target_date, plan_id):
    """Adott dátumhoz tartozó nap sorszámának kiszámítása"""
    start_date = get_plan_start_date(plan_id)
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
    delta = target_date - start_date
    return delta.days + 1  # 1-től kezdve számozunk


def get_date_for_day(day_number, plan_id):
    """Nap sorszámhoz tartozó dátum kiszámítása"""
    start_date = get_plan_start_date(plan_id)
    return start_date + timedelta(days=day_number - 1)


def is_numbered_plan(reading_plan):
    """Ellenőrzi, hogy a terv számozott napokkal működik-e (1, 2, 3...) vagy dátumokkal (MM-DD)"""
    if not reading_plan:
        return False
    first_key = list(reading_plan.keys())[0]
    # Ha az első kulcs csak számokból áll, akkor számozott terv
    return first_key.isdigit()


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
    plan_id = session.get('plan_id')
    
    # Ha nincs dátum megadva, mai napot használjuk
    if date_str is None:
        target_date = date.today()
        date_str = target_date.strftime('%Y-%m-%d')
    else:
        # Dátum parse: támogatjuk YYYY-MM-DD és MM-DD formátumot is
        try:
            if len(date_str) == 10:  # YYYY-MM-DD
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:  # MM-DD (régi kompatibilitás)
                # Használjuk az aktuális évet vagy a terv kezdő évét
                start_date = get_plan_start_date(plan_id)
                month, day = map(int, date_str.split('-'))
                target_date = date(start_date.year, month, day)
                date_str = target_date.strftime('%Y-%m-%d')
        except:
            target_date = date.today()
            date_str = target_date.strftime('%Y-%m-%d')
    
    # Olvasási terv betöltése
    reading_plan = load_reading_plan(plan_id)
    
    # Ellenőrizzük, hogy számozott vagy dátum alapú terv
    out_of_range = False  # Jelzi, ha a dátum a terven kívül esik
    
    if is_numbered_plan(reading_plan):
        # Számozott terv: kiszámoljuk a nap sorszámát
        day_number = get_day_number(target_date, plan_id)
        plan_key = str(day_number)
        
        # Terv maximális napjának meghatározása
        max_day = max(int(k) for k in reading_plan.keys()) if reading_plan else 366
        
        # Ha a nap sorszám kívül esik a terven, ne jelenítsünk meg olvasmányt
        if day_number < 1:
            out_of_range = True
            flash('Ez a dátum a terv kezdete előtt van.', 'warning')
        elif day_number > max_day:
            out_of_range = True
            flash('Ez a dátum a terv végén túl van.', 'warning')
    else:
        # Régi dátum alapú terv (MM-DD)
        day_number = None
        plan_key = target_date.strftime('%m-%d')
    
    # Ha a dátum a terven kívül esik, üres olvasmányokat jelenítünk meg
    if out_of_range:
        daily_readings_raw = {}
    else:
        # Mai szakaszok - átalakítás listává
        daily_readings_raw = reading_plan.get(plan_key, {})
    
    # Szakasz típusok metaadatai
    section_types = {
        'ot': {'name': 'Ószövetség', 'icon': 'bi-bookmark', 'order': 1},
        'nt': {'name': 'Újszövetség', 'icon': 'bi-bookmark-fill', 'order': 2},
        'ps': {'name': 'Zsoltár', 'icon': 'bi-music-note', 'order': 3},
        'pr': {'name': 'Példabeszédek', 'icon': 'bi-lightbulb', 'order': 4},
    }
    
    # Lista formátum készítése
    readings_list = []
    
    # Epoch adatok kinyerése (ha van)
    epoch_data = daily_readings_raw.get('epoch', None)
    
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
    
    # Kommentek és kiemelések (privát szűréssel)
    current_user_id = session.get('user_id')
    comments = get_comments_for_date(date_str, plan_id, current_user_id)
    highlights = get_highlights_for_date(date_str, plan_id, current_user_id)
    
    # Hozzáadjuk, hogy az aktuális user reagált-e már
    for comment in comments:
        comment['user_reacted'] = has_user_reacted(current_user_id, 'comment', comment['id'])
    for highlight in highlights:
        highlight['user_reacted'] = has_user_reacted(current_user_id, 'highlight', highlight['id'])
    
    # Olvasási napló
    user_reading_log = get_reading_log(session['user_id'], plan_id)
    is_read = date_str in user_reading_log
    
    # Kik olvasták már el ezt a napot
    readers = get_readers_for_date(date_str, plan_id)
    readers_count = len(readers)
    
    # Előző és következő nap (teljes dátummal)
    prev_date = target_date - timedelta(days=1)
    next_date = target_date + timedelta(days=1)
    
    prev_str = prev_date.strftime('%Y-%m-%d')
    next_str = next_date.strftime('%Y-%m-%d')
    today_str = date.today().strftime('%Y-%m-%d')
    
    # Dátum megjelenítés formázása
    if out_of_range:
        date_display = format_date_hungarian(target_date)
    elif day_number:
        # Számozott terv: megjelenítjük a nap számát és a dátumot is
        date_display = f"{day_number}. nap ({format_date_hungarian(target_date)})"
    else:
        # Régi formátum: csak a dátum
        date_display = get_date_string(target_date.strftime('%m-%d'))
    
    return render_template('daily.html',
                         date_str=date_str,
                         day_number=day_number,
                         date_display=date_display,
                         readings=readings_list,
                         epoch=epoch_data,
                         comments=comments,
                         highlights=highlights,
                         is_read=is_read,
                         readers=readers,
                         readers_count=readers_count,
                         prev_date=prev_str,
                         next_date=next_str,
                         today=today_str,
                         out_of_range=out_of_range,
                         users=get_all_users(plan_id))


def format_date_hungarian(d):
    """Dátum formázása magyarul (pl. 2025. január 15.)"""
    months = ['január', 'február', 'március', 'április', 'május', 'június',
              'július', 'augusztus', 'szeptember', 'október', 'november', 'december']
    return f"{d.year}. {months[d.month-1]} {d.day}."

@bible_bp.route('/calendar')
@login_required
def calendar():
    """Éves naptár nézet"""
    plan_id = session.get('plan_id')
    reading_plan = load_reading_plan(plan_id)
    user_reading_log = get_reading_log(session['user_id'], plan_id)
    stats = get_all_reading_stats(plan_id)
    
    # Terv kezdő dátuma
    start_date = get_plan_start_date(plan_id)
    numbered_plan = is_numbered_plan(reading_plan)
    total_days = len(reading_plan)
    
    if numbered_plan:
        # Számozott terv: generáljuk a hónapokat a kezdő dátumtól
        from calendar import monthrange
        
        # Számoljuk ki, hogy hány hónapot kell megjeleníteni
        end_date = start_date + timedelta(days=total_days - 1)
        
        months = []
        current_month_start = date(start_date.year, start_date.month, 1)
        
        month_names = ['Január', 'Február', 'Március', 'Április', 'Május', 'Június',
                       'Július', 'Augusztus', 'Szeptember', 'Október', 'November', 'December']
        
        while current_month_start <= end_date:
            days_in_current_month = monthrange(current_month_start.year, current_month_start.month)[1]
            
            month_data = {
                'name': f"{current_month_start.year}. {month_names[current_month_start.month - 1]}",
                'days': []
            }
            
            for d in range(1, days_in_current_month + 1):
                current_date = date(current_month_start.year, current_month_start.month, d)
                date_str = current_date.strftime('%Y-%m-%d')
                
                # Számoljuk ki a nap számát
                day_num = get_day_number(current_date, plan_id)
                
                # Ellenőrizzük, hogy ez a nap a terv része-e
                has_reading = 1 <= day_num <= total_days and str(day_num) in reading_plan
                is_read = date_str in user_reading_log
                is_today = current_date == date.today()
                
                month_data['days'].append({
                    'day': d,
                    'day_number': day_num if has_reading else None,
                    'date_str': date_str,
                    'has_reading': has_reading,
                    'is_read': is_read,
                    'is_today': is_today
                })
            
            months.append(month_data)
            
            # Következő hónap
            if current_month_start.month == 12:
                current_month_start = date(current_month_start.year + 1, 1, 1)
            else:
                current_month_start = date(current_month_start.year, current_month_start.month + 1, 1)
    else:
        # Régi dátum alapú terv
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
                date_key = f"{m+1:02d}-{d:02d}"
                current_date = date(start_date.year, m+1, d)
                date_str = current_date.strftime('%Y-%m-%d')
                has_reading = date_key in reading_plan
                is_read = date_str in user_reading_log
                is_today = current_date == date.today()
                
                month_data['days'].append({
                    'day': d,
                    'day_number': None,
                    'date_str': date_str,
                    'has_reading': has_reading,
                    'is_read': is_read,
                    'is_today': is_today
                })
            months.append(month_data)
    
    return render_template('calendar.html',
                         months=months,
                         stats=stats,
                         total_read=len(user_reading_log),
                         start_date=start_date.strftime('%Y-%m-%d'),
                         numbered_plan=numbered_plan)

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


@bible_bp.route('/api/comment/<int:comment_id>', methods=['PUT'])
@login_required
def api_update_comment(comment_id):
    """Komment szerkesztése"""
    data = request.get_json()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'error': 'Üres komment'}), 400
    
    updated = update_comment(comment_id, session['user_id'], content)
    return jsonify({'success': updated})


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
        raw_notes = get_user_comments(user_id, plan_id)
        # Átalakítjuk a comments formátumot az egységes megjelenítéshez
        notes = []
        for note in raw_notes:
            # Reakciók és válaszok lekérése
            reactions = get_reactions_for_target('comment', note['id'])
            replies = get_replies_for_comment(note['id'])
            notes.append({
                'type': 'comment',
                'id': note['id'],
                'date': note['date'],
                'verse_ref': note.get('verse_ref', ''),
                'text': note['content'],
                'comment_type': note.get('comment_type'),
                'color': None,
                'created_at': note['created_at'],
                'is_private': note.get('is_private', False),
                'reaction_count': len(reactions),
                'reply_count': len(replies)
            })
    elif view_type == 'highlights':
        raw_notes = get_user_highlights(user_id, plan_id)
        # Átalakítjuk a highlights formátumot
        notes = []
        for note in raw_notes:
            # Reakciók lekérése
            reactions = get_reactions_for_target('highlight', note['id'])
            notes.append({
                'type': 'highlight',
                'id': note['id'],
                'date': note['date'],
                'verse_ref': note.get('verse_ref', ''),
                'text': note['text'],
                'comment_type': None,
                'color': note.get('color', 'yellow'),
                'created_at': note['created_at'],
                'is_private': note.get('is_private', False),
                'reaction_count': len(reactions)
            })
    else:
        raw_notes = get_user_notes_combined(user_id, plan_id)
        # Reakciók és válaszok hozzáadása a kombinált jegyzetekhez
        notes = []
        for note in raw_notes:
            reactions = get_reactions_for_target(note['type'], note['id'])
            note_data = dict(note)
            note_data['reaction_count'] = len(reactions)
            if note['type'] == 'comment':
                replies = get_replies_for_comment(note['id'])
                note_data['reply_count'] = len(replies)
            else:
                note_data['reply_count'] = 0
            notes.append(note_data)
    
    # Statisztikák
    total_comments = len(get_user_comments(user_id, plan_id))
    total_highlights = len(get_user_highlights(user_id, plan_id))
    
    return render_template('my_notes.html',
                         notes=notes,
                         view_type=view_type,
                         total_comments=total_comments,
                         total_highlights=total_highlights,
                         username=session.get('username'))


# ==========================================
# Reakció API végpontok
# ==========================================

@bible_bp.route('/api/reaction', methods=['POST'])
@login_required
def api_toggle_reaction():
    """Reakció hozzáadása/eltávolítása (toggle)"""
    data = request.get_json()
    target_type = data.get('target_type')  # 'comment' vagy 'highlight'
    target_id = data.get('target_id')
    user_id = session.get('user_id')
    
    if not target_type or not target_id:
        return jsonify({'success': False, 'error': 'Hiányzó paraméterek'}), 400
    if target_type not in ('comment', 'highlight'):
        return jsonify({'success': False, 'error': 'Érvénytelen target_type'}), 400
    
    # Ellenőrizzük, hogy már reagált-e
    if has_user_reacted(user_id, target_type, target_id):
        # Eltávolítjuk a reakciót
        count = remove_reaction(user_id, target_type, target_id)
        return jsonify({'success': True, 'action': 'removed', 'count': count})
    else:
        # Hozzáadjuk a reakciót
        result = add_reaction(user_id, target_type, target_id)
        if result['success']:
            return jsonify({'success': True, 'action': 'added', 'count': result['count']})
        else:
            return jsonify({'success': False, 'error': result['error']}), 400


# ==========================================
# Válasz komment API végpontok
# ==========================================

@bible_bp.route('/api/comment/<int:comment_id>/reply', methods=['POST'])
@login_required
def api_add_reply(comment_id):
    """Válasz hozzáadása egy kommenthez"""
    data = request.get_json()
    content = data.get('content', '').strip()
    user_id = session.get('user_id')
    username = session.get('username')
    
    if not content:
        return jsonify({'success': False, 'error': 'A válasz nem lehet üres'}), 400
    
    reply_id = add_comment_reply(user_id, comment_id, content)
    
    return jsonify({
        'success': True,
        'id': reply_id,
        'user_name': username,
        'content': content
    })


@bible_bp.route('/api/reply/<int:reply_id>', methods=['DELETE'])
@login_required
def api_delete_reply(reply_id):
    """Válasz törlése"""
    user_id = session.get('user_id')
    deleted = delete_comment_reply(reply_id, user_id)
    
    if deleted:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Nem sikerült törölni'}), 400


# ==========================================
# Privát beállítás API végpontok
# ==========================================

@bible_bp.route('/api/comment/<int:comment_id>/privacy', methods=['PUT'])
@login_required
def api_update_comment_privacy(comment_id):
    """Komment privát státuszának módosítása"""
    data = request.get_json()
    is_private = data.get('is_private', False)
    user_id = session.get('user_id')
    
    updated = update_comment_privacy(comment_id, user_id, is_private)
    
    if updated:
        return jsonify({'success': True, 'is_private': is_private})
    else:
        return jsonify({'success': False, 'error': 'Nem sikerült módosítani'}), 400


@bible_bp.route('/api/highlight/<int:highlight_id>/privacy', methods=['PUT'])
@login_required
def api_update_highlight_privacy(highlight_id):
    """Kiemelés privát státuszának módosítása"""
    data = request.get_json()
    is_private = data.get('is_private', False)
    user_id = session.get('user_id')
    
    updated = update_highlight_privacy(highlight_id, user_id, is_private)
    
    if updated:
        return jsonify({'success': True, 'is_private': is_private})
    else:
        return jsonify({'success': False, 'error': 'Nem sikerült módosítani'}), 400
