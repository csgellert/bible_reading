import os
from dotenv import load_dotenv

# .env fájl betöltése
load_dotenv()

class Config:
    # Titkos kulcs a session-ökhöz
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Központi jelszó a weboldalhoz (alapértelmezett terv létrehozásához)
    SITE_PASSWORD = os.environ.get('SITE_PASSWORD', 'biblia2025')
    
    # Adatbázis elérési út
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'bible.db')
    
    # Olvasási terv JSON fájl
    READING_PLAN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'reading_plan.json')
    
    # ==========================================
    # Biblia szöveg forrás beállítások
    # ==========================================
    
    # Biblia szöveg forrása: 'api' vagy 'local'
    BIBLE_SOURCE = os.environ.get('BIBLE_SOURCE', 'api')
    
    # API fordítás (csak 'api' forrás esetén)
    # Lehetséges értékek: SZIT, KNB, RUF, KG, stb.
    BIBLE_TRANSLATION = os.environ.get('BIBLE_TRANSLATION', 'SZIT')
    
    # API alap URL
    BIBLE_API_URL = os.environ.get('BIBLE_API_URL', 'https://szentiras.eu/api')
