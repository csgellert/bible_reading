from flask import Flask
from datetime import timedelta
import argparse
import os
from config import Config
from models.database import init_db

def create_app(bible_source=None, bible_translation=None):
    app = Flask(__name__)
    
    # Konfiguráció betöltése
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY
    
    # Parancssori beállítások felülírása
    if bible_source:
        app.config['BIBLE_SOURCE'] = bible_source
    else:
        app.config['BIBLE_SOURCE'] = Config.BIBLE_SOURCE
        
    if bible_translation:
        app.config['BIBLE_TRANSLATION'] = bible_translation
    else:
        app.config['BIBLE_TRANSLATION'] = Config.BIBLE_TRANSLATION
    
    app.config['BIBLE_API_URL'] = Config.BIBLE_API_URL
    
    # Session beállítások
    app.permanent_session_lifetime = timedelta(days=31)
    
    # Adatbázis inicializálása
    init_db()
    
    # Blueprint-ek regisztrálása
    from routes.auth import auth_bp
    from routes.bible import bible_bp
    from routes.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(bible_bp)
    app.register_blueprint(admin_bp)
    
    return app

if __name__ == '__main__':
    # Parancssori argumentumok
    parser = argparse.ArgumentParser(description='Biblia Olvasási Terv Szerver')
    parser.add_argument(
        '--bible-source', '-s',
        choices=['api', 'local'],
        default=None,
        help='Biblia szöveg forrása: api (szentiras.eu) vagy local (helyi adatbázis)'
    )
    parser.add_argument(
        '--translation', '-t',
        default=None,
        help='Biblia fordítás (pl. SZIT, KNB, RUF, KG)'
    )
    parser.add_argument(
        '--host', '-H',
        default='0.0.0.0',
        help='Szerver host cím (alapértelmezett: 0.0.0.0)'
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=5000,
        help='Szerver port (alapértelmezett: 5000)'
    )
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        default=True,
        help='Debug mód bekapcsolása'
    )
    
    args = parser.parse_args()
    
    # Információ kiirása
    print("="*50)
    print("Biblia Olvasási Terv - Szerver")
    print("="*50)
    
    source = args.bible_source or os.environ.get('BIBLE_SOURCE') or 'api'
    translation = args.translation or os.environ.get('BIBLE_TRANSLATION') or 'SZIT'
    
    print(f"Biblia forrás: {source}")
    if source == 'api':
        print(f"Fordítás: {translation}")
        print(f"API: https://szentiras.eu")
    else:
        print("Helyi adatbázis (még nincs implementálva)")
    print(f"Szerver: http://{args.host}:{args.port}")
    print("="*50)
    
    app = create_app(
        bible_source=args.bible_source,
        bible_translation=args.translation
    )
    app.run(debug=args.debug, host=args.host, port=args.port)
