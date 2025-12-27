import os

class Config:
    # Titkos kulcs a session-ökhöz - éles környezetben cseréld le!
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'biblia-olvasasi-terv-2025-titkos-kulcs'
    
    # Központi jelszó a weboldalhoz - ezt változtasd meg!
    SITE_PASSWORD = os.environ.get('SITE_PASSWORD') or 'biblia2025'
    
    # Adatbázis elérési út
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'bible.db')
    
    # Olvasási terv JSON fájl
    READING_PLAN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'reading_plan.json')
    
    # ==========================================
    # Biblia szöveg forrás beállítások
    # ==========================================
    
    # Biblia szöveg forrása: 'api' vagy 'local'
    # - 'api': szentiras.eu API-ból tölti le a szöveget
    # - 'local': helyi adatbázisból veszi (még nincs implementálva)
    BIBLE_SOURCE = os.environ.get('BIBLE_SOURCE') or 'api'
    
    # API fordítás (csak 'api' forrás esetén)
    # Lehetséges értékek: SZIT, KNB, RUF, KG, stb.
    # - SZIT: Szent István Társulat fordítása (katolikus)
    # - KNB: Kenesei Biblia
    # - RUF: Református új fordítás
    # - KG: Károli Gáspár
    BIBLE_TRANSLATION = os.environ.get('BIBLE_TRANSLATION') or 'SZIT'
    
    # API alap URL
    BIBLE_API_URL = os.environ.get('BIBLE_API_URL') or 'https://szentiras.eu/api'
