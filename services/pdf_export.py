"""
PDF export szolgáltatás - Kiemelések exportálása
"""

import io
import os
from datetime import datetime
from fpdf import FPDF

# Font elérési út
FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'fonts')


class HighlightsPDF(FPDF):
    """Egyedi PDF osztály kiemelések exportálásához"""
    
    def __init__(self, username, plan_name):
        super().__init__()
        self.username = username
        self.plan_name = plan_name or 'Bibliaolvasási Terv'
        # Unicode font regisztrálása
        self.add_font('DejaVu', '', os.path.join(FONT_DIR, 'DejaVuSans.ttf'))
        self.add_font('DejaVu', 'B', os.path.join(FONT_DIR, 'DejaVuSans-Bold.ttf'))
        self.add_font('DejaVu', 'I', os.path.join(FONT_DIR, 'DejaVuSans-Oblique.ttf'))
        self.add_page()
        self.set_auto_page_break(auto=True, margin=20)
    
    def header(self):
        self.set_font('DejaVu', 'B', 10)
        self.set_text_color(90, 124, 101)  # --color-primary
        self.cell(0, 8, self.plan_name, align='L')
        self.cell(0, 8, self.username, align='R', new_x='LMARGIN', new_y='NEXT')
        self.set_draw_color(90, 124, 101)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'{self.page_no()}/{{nb}}', align='C')


def generate_highlights_pdf(highlights, username, plan_name, day_number_fn=None):
    """
    Kiemelések PDF generálása.
    
    Args:
        highlights: Lista a kiemelésekből (dict: date, verse_ref, text, created_at)
        username: Felhasználónév
        plan_name: Olvasási terv neve
        day_number_fn: Függvény, ami dátumból nap számot ad vissza (opcionális)
    
    Returns:
        bytes: PDF tartalom
    """
    pdf = HighlightsPDF(username, plan_name)
    pdf.alias_nb_pages()
    
    # Cím
    pdf.set_font('DejaVu', 'B', 18)
    pdf.set_text_color(61, 90, 69)  # --color-primary-dark
    pdf.cell(0, 12, 'Kiemeléseim', align='C', new_x='LMARGIN', new_y='NEXT')
    
    pdf.set_font('DejaVu', '', 10)
    pdf.set_text_color(107, 114, 128)
    date_str = datetime.now().strftime('%Y. %m. %d.')
    pdf.cell(0, 6, f'Exportálva: {date_str}  |  Összesen: {len(highlights)} kiemelés',
             align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(6)
    
    if not highlights:
        pdf.set_font('DejaVu', 'I', 12)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 20, 'Nincsenek kiemelések.', align='C')
        return _pdf_to_bytes(pdf)
    
    # Kiemelések csoportosítása dátum szerint
    grouped = {}
    for h in highlights:
        date_key = h.get('date', 'Ismeretlen')
        if date_key not in grouped:
            grouped[date_key] = []
        grouped[date_key].append(h)
    
    # Rendezés dátum szerint
    sorted_dates = sorted(grouped.keys())
    
    for date_key in sorted_dates:
        items = grouped[date_key]
        
        # Nap fejléc
        day_label = date_key
        if day_number_fn:
            try:
                day_num = day_number_fn(date_key)
                if day_num and 1 <= day_num <= 366:
                    day_label = f'{day_num}. nap  ({date_key})'
            except Exception:
                pass
        
        # Fejléc sáv
        pdf.set_fill_color(240, 248, 242)  # halvány zöld
        pdf.set_draw_color(90, 124, 101)
        pdf.set_font('DejaVu', 'B', 11)
        pdf.set_text_color(61, 90, 69)
        pdf.cell(0, 8, f'  {day_label}', fill=True, border='L',
                 new_x='LMARGIN', new_y='NEXT')
        pdf.ln(2)
        
        for item in items:
            verse_ref = item.get('verse_ref', '')
            text = item.get('text', '')
            
            # Igehely
            if verse_ref:
                pdf.set_font('DejaVu', 'B', 10)
                pdf.set_text_color(90, 124, 101)
                pdf.cell(0, 5, verse_ref, new_x='LMARGIN', new_y='NEXT')
            
            # Kiemelés szövege
            pdf.set_font('DejaVu', '', 10)
            pdf.set_text_color(58, 58, 58)
            pdf.set_x(15)
            pdf.set_draw_color(201, 162, 39)  # arany szín a bal szegélyhez
            y_before = pdf.get_y()
            pdf.multi_cell(175, 5, f'\u201e{text}\u201d', new_x='LMARGIN', new_y='NEXT')
            y_after = pdf.get_y()
            # Bal oldali arany vonal
            pdf.line(13, y_before, 13, y_after)
            
            pdf.ln(3)
        
        pdf.ln(2)
    
    return _pdf_to_bytes(pdf)


def _pdf_to_bytes(pdf):
    """PDF objektum byte-okká alakítása"""
    return bytes(pdf.output())
