"""
PDF export szolgáltatás - Kiemelések exportálása
"""

import io
import os
import re
from datetime import datetime
from fpdf import FPDF

# Font elérési út
FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'fonts')

# Színpaletta (bambusz/zöld téma)
C_PRIMARY = (90, 124, 101)       # #5a7c65
C_PRIMARY_DARK = (61, 90, 69)    # #3d5a45
C_BG = (250, 249, 247)           # #faf9f7 — drapp háttér
C_BG_SECTION = (245, 244, 240)   # #f5f4f0
C_ACCENT = (201, 162, 39)        # #c9a227 — arany
C_TEXT = (58, 58, 58)            # fő szöveg
C_TEXT_MUTED = (140, 140, 135)   # halvány szöveg


class HighlightsPDF(FPDF):
    """Egyedi PDF osztály kiemelések exportálásához"""
    
    def __init__(self, username, plan_name):
        super().__init__()
        self.username = username
        self.plan_name = plan_name or 'Bibliaolvasási Terv'
        self.add_font('DejaVu', '', os.path.join(FONT_DIR, 'DejaVuSans.ttf'))
        self.add_font('DejaVu', 'B', os.path.join(FONT_DIR, 'DejaVuSans-Bold.ttf'))
        self.add_font('DejaVu', 'I', os.path.join(FONT_DIR, 'DejaVuSans-Oblique.ttf'))
        self.set_auto_page_break(auto=True, margin=18)
    
    def _draw_bg(self):
        """Drapp háttér az egész oldalra"""
        self.set_fill_color(*C_BG)
        self.rect(0, 0, 210, 297, 'F')
    
    def header(self):
        self._draw_bg()
        self.set_font('DejaVu', '', 7)
        self.set_text_color(*C_TEXT_MUTED)
        self.cell(0, 6, self.plan_name, align='L')
        self.cell(0, 6, self.username, align='R', new_x='LMARGIN', new_y='NEXT')
        self.set_draw_color(*C_PRIMARY)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)
    
    def footer(self):
        self.set_y(-14)
        self.set_font('DejaVu', '', 7)
        self.set_text_color(*C_TEXT_MUTED)
        self.cell(0, 8, f'{self.page_no()} / {{nb}}', align='C')


def generate_highlights_pdf(highlights, username, plan_name, day_number_fn=None):
    """
    Kiemelések PDF generálása.
    """
    pdf = HighlightsPDF(username, plan_name)
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Cím
    pdf.set_font('DejaVu', 'B', 14)
    pdf.set_text_color(*C_PRIMARY_DARK)
    pdf.cell(0, 10, 'Kiemeléseim', align='C', new_x='LMARGIN', new_y='NEXT')
    
    pdf.set_font('DejaVu', '', 8)
    pdf.set_text_color(*C_TEXT_MUTED)
    date_str = datetime.now().strftime('%Y. %m. %d.')
    pdf.cell(0, 5, f'Exportálva: {date_str}  \u00b7  {len(highlights)} kiemelés',
             align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(5)
    
    if not highlights:
        pdf.set_font('DejaVu', 'I', 9)
        pdf.set_text_color(*C_TEXT_MUTED)
        pdf.cell(0, 15, 'Nincsenek kiemelések.', align='C')
        return _pdf_to_bytes(pdf)
    
    # Kiemelések csoportosítása dátum szerint
    grouped = {}
    for h in highlights:
        date_key = h.get('date', 'Ismeretlen')
        if date_key not in grouped:
            grouped[date_key] = []
        grouped[date_key].append(h)
    
    sorted_dates = sorted(grouped.keys())
    
    for date_key in sorted_dates:
        items = grouped[date_key]
        
        # Nap meghatározása
        day_label = date_key
        if day_number_fn:
            try:
                day_num = day_number_fn(date_key)
                if day_num and 1 <= day_num <= 366:
                    day_label = f'{day_num}. nap  \u00b7  {date_key}'
            except Exception:
                pass
        
        # Nap fejléc — kompakt, zöld szegéllyel
        pdf.set_draw_color(*C_PRIMARY)
        pdf.set_line_width(0.6)
        y = pdf.get_y()
        pdf.line(10, y, 10, y + 5)
        pdf.set_x(13)
        pdf.set_font('DejaVu', 'B', 8.5)
        pdf.set_text_color(*C_PRIMARY_DARK)
        pdf.cell(0, 5, day_label, new_x='LMARGIN', new_y='NEXT')
        pdf.ln(1.5)
        
        for item in items:
            verse_ref = item.get('verse_ref', '')
            text = _strip_verse_numbers(item.get('text', ''))
            
            # Igehely és szöveg egy blokkban
            x_start = 13  # Arany szegély pozíciója
            x_content = 15  # Szöveg pozíciója
            
            if verse_ref:
                pdf.set_x(x_content)
                pdf.set_font('DejaVu', 'B', 8)
                pdf.set_text_color(*C_PRIMARY)
                pdf.cell(0, 4.5, verse_ref, new_x='LMARGIN', new_y='NEXT')
            
            # Szöveg téglalappal és baloldali arany szegéllyel
            pdf.set_x(x_content)
            pdf.set_font('DejaVu', '', 8.5)
            pdf.set_text_color(*C_TEXT)
            pdf.set_draw_color(*C_ACCENT)  # Arany
            pdf.set_line_width(0.4)
            
            # border='L' automatikusan rajzolja a baloldali szegélyt az oldaltöréseknél is
            pdf.multi_cell(175, 4.5, f'\u201e{text}\u201d', border='L', 
                          new_x='LMARGIN', new_y='NEXT')
            
            pdf.ln(2)
        
        pdf.ln(1.5)
    
    return _pdf_to_bytes(pdf)


def _strip_verse_numbers(text):
    """Versjelző számok eltávolítása a kiemelt szövegből.
    
    A böngészős kijelölés a <sup class="verse-num"> tartalmakat
    beleolvasztja a szövegbe, pl. '...legyen.17János tanú...'.
    """
    if not text:
        return text
    # Szám az elején: "16Mert úgy..." -> "Mert úgy..."
    text = re.sub(r'^\d{1,3}(?=[A-ZÁÉÍÓÖŐÚÜŰa-záéíóöőúüű(\[\u201e])', '', text)
    # Szám szövegben: "...legyen.17János..." -> "...legyen. János..."
    text = re.sub(r'([.!?\u201d"\)\]])\d{1,3}(?=[A-ZÁÉÍÓÖŐÚÜŰa-záéíóöőúüű(\[\u201e])', r'\1 ', text)
    # Szám szóköz után: "...legyen. 17János..." -> "...legyen. János..."
    text = re.sub(r'\s\d{1,3}(?=[A-ZÁÉÍÓÖŐÚÜŰa-záéíóöőúüű(\[\u201e])', ' ', text)
    return text.strip()


def _pdf_to_bytes(pdf):
    """PDF objektum byte-okká alakítása"""
    return bytes(pdf.output())
