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
