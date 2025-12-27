"""
Szentírás API szolgáltatás
Forrás: https://szentiras.eu/api
"""

import requests
import re
from flask import current_app

# Elérhető fordítások
AVAILABLE_TRANSLATIONS = {
    'SZIT': {
        'name': 'Szent István Társulat',
        'short': 'SZIT',
        'description': 'Katolikus fordítás (2013)',
        'default': True
    },
    'KNB': {
        'name': 'Káldi Neovulgáta',
        'short': 'KNB',
        'description': 'Katolikus fordítás (1997)',
        'default': False
    },
    'RUF': {
        'name': 'Református Új Fordítás',
        'short': 'RUF',
        'description': 'Protestáns fordítás (2014)',
        'default': False
    },
    'KG': {
        'name': 'Károli Gáspár',
        'short': 'KG',
        'description': 'Klasszikus protestáns (1908)',
        'default': False
    },
    'UF': {
        'name': 'Új Fordítás',
        'short': 'UF',
        'description': 'Protestáns fordítás (1975)',
        'default': False
    }
}


def get_available_translations():
    """Visszaadja az elérhető fordítások listáját"""
    return AVAILABLE_TRANSLATIONS


def process_verse_html(text):
    """
    Feldolgozza a vers szöveget, megtartva a fontos HTML elemeket.
    
    - <h5>, <h4>, stb. -> szakasz cím (vastagított)
    - <i>, <em> -> dőlt
    - Többi HTML tag eltávolítása
    """
    if not text:
        return ''
    
    # Fejléc tagek átalakítása span-ra vastagított címként
    # <h5>Cím</h5> -> <span class="section-title">Cím</span>
    text = re.sub(
        r'<h[1-6][^>]*>(.*?)</h[1-6]>',
        r'<span class="section-title">\1</span> ',
        text,
        flags=re.IGNORECASE | re.DOTALL
    )
    
    # Dőlt tagek megtartása
    text = re.sub(r'<(em|i)>(.*?)</(em|i)>', r'<em>\2</em>', text, flags=re.IGNORECASE)
    
    # Vastag tagek megtartása
    text = re.sub(r'<(strong|b)>(.*?)</(strong|b)>', r'<strong>\2</strong>', text, flags=re.IGNORECASE)
    
    # Minden más HTML tag eltávolítása
    text = re.sub(r'<(?!/?(?:em|strong|span)[^>]*>)[^>]+>', '', text)
    
    return text.strip()


# Könyv nevek átalakítása az API formátumra
BOOK_MAPPINGS = {
    # Ószövetség
    '1mózes': '1Móz', '1móz': '1Móz', 'genezis': '1Móz', 'ter': '1Móz',
    '2mózes': '2Móz', '2móz': '2Móz', 'exodus': '2Móz', 'kiv': '2Móz',
    '3mózes': '3Móz', '3móz': '3Móz', 'leviticus': '3Móz', 'lev': '3Móz',
    '4mózes': '4Móz', '4móz': '4Móz', 'numeri': '4Móz', 'szám': '4Móz',
    '5mózes': '5Móz', '5móz': '5Móz', 'deuteronomium': '5Móz', 'mtörv': '5Móz',
    'józsué': 'Józs', 'józs': 'Józs',
    'bírák': 'Bír', 'bír': 'Bír',
    'ruth': 'Ruth', 'rut': 'Ruth',
    '1sámuel': '1Sám', '1sám': '1Sám',
    '2sámuel': '2Sám', '2sám': '2Sám',
    '1királyok': '1Kir', '1kir': '1Kir',
    '2királyok': '2Kir', '2kir': '2Kir',
    '1krónikák': '1Krón', '1krón': '1Krón',
    '2krónikák': '2Krón', '2krón': '2Krón',
    'ezsdrás': 'Ezsd', 'ezsd': 'Ezsd',
    'nehémiás': 'Neh', 'neh': 'Neh',
    'eszter': 'Eszt', 'eszt': 'Eszt',
    'jób': 'Jób',
    'zsoltárok': 'Zsolt', 'zsoltár': 'Zsolt', 'zsolt': 'Zsolt',
    'példabeszédek': 'Péld', 'péld': 'Péld',
    'prédikátor': 'Préd', 'préd': 'Préd',
    'énekek éneke': 'Én', 'én': 'Én',
    'ézsaiás': 'Ézs', 'ézs': 'Ézs', 'izajás': 'Ézs',
    'jeremiás': 'Jer', 'jer': 'Jer',
    'siralmak': 'Siral', 'jsir': 'Siral',
    'ezékiel': 'Ez', 'ez': 'Ez',
    'dániel': 'Dán', 'dán': 'Dán',
    'hóseás': 'Hós', 'hós': 'Hós',
    'jóel': 'Jóel',
    'ámósz': 'Ám', 'ám': 'Ám',
    'abdiás': 'Abd', 'abd': 'Abd',
    'jónás': 'Jón', 'jón': 'Jón',
    'mikeás': 'Mik', 'mik': 'Mik',
    'náhum': 'Náh', 'náh': 'Náh',
    'habakuk': 'Hab', 'hab': 'Hab',
    'zofóniás': 'Zof', 'zof': 'Zof',
    'haggeus': 'Hag', 'hag': 'Hag',
    'zakariás': 'Zak', 'zak': 'Zak',
    'malakiás': 'Mal', 'mal': 'Mal',
    
    # Újszövetség
    'máté': 'Mt', 'mt': 'Mt',
    'márk': 'Mk', 'mk': 'Mk',
    'lukács': 'Lk', 'lk': 'Lk',
    'jános': 'Jn', 'jn': 'Jn',
    'apostolok cselekedetei': 'ApCsel', 'apcsel': 'ApCsel', 'csel': 'ApCsel',
    'róma': 'Róm', 'róm': 'Róm', 'rómaiakhoz': 'Róm',
    '1korinthus': '1Kor', '1kor': '1Kor',
    '2korinthus': '2Kor', '2kor': '2Kor',
    'galata': 'Gal', 'gal': 'Gal',
    'efezus': 'Ef', 'ef': 'Ef',
    'filippi': 'Fil', 'fil': 'Fil',
    'kolossé': 'Kol', 'kol': 'Kol',
    '1thesszalonika': '1Thessz', '1thessz': '1Thessz',
    '2thesszalonika': '2Thessz', '2thessz': '2Thessz',
    '1timóteus': '1Tim', '1tim': '1Tim',
    '2timóteus': '2Tim', '2tim': '2Tim',
    'titusz': 'Tit', 'tit': 'Tit',
    'filemon': 'Filem', 'filem': 'Filem',
    'zsidók': 'Zsid', 'zsid': 'Zsid',
    'jakab': 'Jak', 'jak': 'Jak',
    '1péter': '1Pt', '1pt': '1Pt',
    '2péter': '2Pt', '2pt': '2Pt',
    '1jános': '1Jn', '1jn': '1Jn',
    '2jános': '2Jn', '2jn': '2Jn',
    '3jános': '3Jn', '3jn': '3Jn',
    'júdás': 'Júd', 'júd': 'Júd',
    'jelenések': 'Jel', 'jel': 'Jel',
}


def normalize_reference(reference):
    """
    Átalakítja a hivatkozást az API által elfogadott formátumra.
    Pl: "1Mózes 1-3" -> "1Móz1-3"
    """
    if not reference:
        return None
    
    # Tisztítás
    ref = reference.strip()
    
    # Próbáljuk megtalálni a könyv nevét és a fejezet/vers számokat
    # Minta: "1Mózes 1-3" vagy "Máté 5:1-26" vagy "Zsoltár 1"
    
    # Számmal kezdődő könyvek kezelése (1Mózes, 2Királyok, stb.)
    match = re.match(r'^(\d?\s*[A-Za-zÁÉÍÓÖŐÚÜŰáéíóöőúüű]+)\s*(.*)$', ref, re.IGNORECASE)
    
    if match:
        book_name = match.group(1).strip().lower()
        chapter_verse = match.group(2).strip()
        
        # Könyv név normalizálása
        # Távolítsuk el a szóközöket a számok és betűk között
        book_name = re.sub(r'(\d)\s+', r'\1', book_name)
        
        # Keressük meg a megfelelő API könyv nevet
        api_book = None
        for key, value in BOOK_MAPPINGS.items():
            if book_name == key or book_name.startswith(key):
                api_book = value
                break
        
        if api_book:
            # Összeállítjuk az API hivatkozást (szóköz nélkül)
            return f"{api_book}{chapter_verse}"
    
    # Ha nem sikerült feldolgozni, próbáljuk közvetlenül
    # Eltávolítjuk a szóközöket
    return ref.replace(' ', '')


def fetch_verses_from_api(reference, translation='SZIT'):
    """
    Lekéri a verseket a szentiras.eu API-ból.
    
    Args:
        reference: Szentírási hivatkozás (pl. "1Mózes 1-3", "Mt5")
        translation: Fordítás kódja (SZIT, KNB, RUF, KG, stb.)
    
    Returns:
        dict: {
            'success': bool,
            'verses': [{'text': str, 'reference': str}],
            'full_reference': str,
            'error': str (ha hiba történt)
        }
    """
    try:
        # Hivatkozás normalizálása
        api_ref = normalize_reference(reference)
        if not api_ref:
            return {
                'success': False,
                'error': 'Érvénytelen hivatkozás',
                'verses': [],
                'full_reference': reference
            }
        
        # API URL összeállítása
        url = f"https://szentiras.eu/api/idezet/{api_ref}/{translation}"
        
        # Debug: kiírjuk a lekérdezést
        print(f"[DEBUG] API lekérdezés: {url}")
        print(f"[DEBUG] Eredeti hivatkozás: '{reference}' -> Normalizált: '{api_ref}'")
        
        # Lekérés
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Debug: válasz struktúra
        print(f"[DEBUG] API válasz kulcsok: {list(data.keys())}")
        
        # Versek feldolgozása - a helyes útvonal: valasz.versek
        verses = []
        full_reference = reference
        
        # A szentiras.eu API válasz formátuma: { keres: {...}, valasz: { versek: [...] } }
        valasz = data.get('valasz', {})
        versek_list = valasz.get('versek', [])
        
        print(f"[DEBUG] Talált versek száma: {len(versek_list)}")
        
        if versek_list:
            for vers in versek_list:
                # A mező neve 'szoveg' (nem 'szöveg')
                verse_text = vers.get('szoveg', '')
                hely = vers.get('hely', {})
                verse_ref = hely.get('szep', '')
                
                # HTML tagek feldolgozása - fejlécek megtartása formázottan
                verse_text = process_verse_html(verse_text)
                
                verses.append({
                    'text': verse_text,
                    'reference': verse_ref
                })
                
                # Az első vers helyéből vesszük a szép hivatkozást
                if not full_reference or full_reference == reference:
                    if verse_ref:
                        full_reference = verse_ref
            
            print(f"[DEBUG] Feldolgozott versek: {len(verses)}")
        
        if verses:
            return {
                'success': True,
                'verses': verses,
                'full_reference': full_reference,
                'error': None
            }
        else:
            print(f"[DEBUG] Nincs vers a válaszban!")
            return {
                'success': False,
                'error': 'Nem található vers',
                'verses': [],
                'full_reference': reference
            }
            
    except requests.exceptions.Timeout:
        print(f"[DEBUG] API időtúllépés: {url}")
        return {
            'success': False,
            'error': 'API időtúllépés',
            'verses': [],
            'full_reference': reference
        }
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] Hálózati hiba: {e}")
        return {
            'success': False,
            'error': f'Hálózati hiba: {str(e)}',
            'verses': [],
            'full_reference': reference
        }
    except Exception as e:
        print(f"[DEBUG] Általános hiba: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': f'Hiba: {str(e)}',
            'verses': [],
            'full_reference': reference
        }


def format_verses_html(verses_data):
    """
    Formázza a verseket HTML-ként megjelenítésre.
    
    Args:
        verses_data: A fetch_verses_from_api visszatérési értéke
    
    Returns:
        str: HTML formázott szöveg
    """
    if not verses_data.get('success'):
        error = verses_data.get('error', 'Ismeretlen hiba')
        return f'<p class="text-muted fst-italic"><i class="bi bi-exclamation-triangle"></i> {error}</p>'
    
    html_parts = []
    current_chapter = None
    
    # Számoljuk meg, hány különböző fejezet van
    chapters_in_reading = set()
    for verse in verses_data.get('verses', []):
        ref = verse.get('reference', '')
        chapter_match = re.search(r'(\d+),', ref)
        if chapter_match:
            chapters_in_reading.add(chapter_match.group(1))
    
    # Csak akkor jelenítjük meg a fejezetszámot, ha több fejezet van
    show_chapter_headers = len(chapters_in_reading) > 1
    
    for verse in verses_data.get('verses', []):
        text = verse.get('text', '')
        ref = verse.get('reference', '')
        
        # Vers szám kinyerése a hivatkozásból
        verse_num_match = re.search(r',(\d+)$', ref)
        verse_num = verse_num_match.group(1) if verse_num_match else ''
        
        # Fejezet kinyerése
        chapter_match = re.search(r'(\d+),', ref)
        chapter = chapter_match.group(1) if chapter_match else ''
        
        # Új fejezet jelzése fejezetszámmal
        if chapter and chapter != current_chapter:
            if show_chapter_headers:
                # Kis hely az előző fejezet után
                if current_chapter is not None:
                    html_parts.append('<span class="chapter-break"></span>')
                # Nagy fejezetszám a szöveg elején
                html_parts.append(f'<span class="chapter-number">{chapter}</span>')
            elif current_chapter is not None:
                html_parts.append('<br><br>')
            current_chapter = chapter
        
        # Ellenőrizzük, hogy van-e szakasz cím a szövegben
        has_section_title = 'section-title' in text
        
        # Vers hozzáadása
        if verse_num:
            # Ha van szakasz cím, előtte új sor
            if has_section_title and html_parts:
                html_parts.append('<br>')
            
            html_parts.append(
                f'<span class="verse" data-verse="{verse_num}">'
                f'<sup class="verse-num">{verse_num}</sup>{text}</span> '
            )
        else:
            html_parts.append(f'<span class="verse">{text}</span> ')
    
    return ''.join(html_parts)
