# Services __init__.py
from .bible_api import (
    fetch_verses_from_api, 
    format_verses_html, 
    normalize_reference,
    get_available_translations,
    AVAILABLE_TRANSLATIONS
)
