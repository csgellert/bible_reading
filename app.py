from flask import Flask
from datetime import timedelta
from config import Config
from models.database import init_db

def create_app():
    app = Flask(__name__)
    
    # Konfiguráció betöltése
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY
    
    # Session beállítások
    app.permanent_session_lifetime = timedelta(days=31)
    
    # Adatbázis inicializálása
    init_db()
    
    # Blueprint-ek regisztrálása
    from routes.auth import auth_bp
    from routes.bible import bible_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(bible_bp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
