"""PDF del mismo contenido HTML que se imprime, sin servicios externos."""
from html import escape
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer


class ContenidoTicket(HTMLParser):
    def __init__(self):
        super().__init__()
        self.bloques = []
        self.tag = None
        self.partes = []

    def handle_starttag(self, tag, attrs):
        if tag in ('p', 'h2', 'dt', 'dd'):
            self.tag, self.partes = tag, []
        elif tag == 'br' and self.tag:
            self.partes.append('\n')

    def handle_data(self, data):
        if self.tag:
            self.partes.append(data)

    def handle_endtag(self, tag):
        if tag == self.tag:
            texto = ' '.join(''.join(self.partes).split())
            if texto:
                self.bloques.append((tag, texto))
            self.tag = None


def generar_ticket_pdf(html, numero):
    contenido = ContenidoTicket()
    contenido.feed(html)
    normal = ParagraphStyle('normal', fontName='Helvetica', fontSize=9, leading=12, spaceAfter=5)
    estilos = {
        'dd': normal,
        'dt': ParagraphStyle('label', parent=normal, fontName='Helvetica-Bold', fontSize=8, spaceAfter=1, keepWithNext=True),
        'p': ParagraphStyle('centrado', parent=normal, alignment=1, fontSize=8, leading=11),
        'h2': ParagraphStyle('titulo', parent=normal, fontName='Helvetica-Bold', alignment=1, fontSize=12, leading=15),
    }
    flujo = []
    logo = Path(__file__).resolve().parents[1] / 'static/images/logo-ticket-servitech.png'
    if logo.exists():
        imagen = Image(str(logo))
        imagen.drawHeight *= (45 * mm) / imagen.drawWidth
        imagen.drawWidth = 45 * mm
        flujo.extend([imagen, Spacer(1, 3 * mm)])
    for tag, texto in contenido.bloques:
        flujo.append(Paragraph(escape(texto), estilos[tag]))
    salida = BytesIO()
    documento = SimpleDocTemplate(salida, pagesize=(80 * mm, 297 * mm),
        leftMargin=4*mm, rightMargin=4*mm, topMargin=4*mm, bottomMargin=5*mm,
        title=f'Ticket {numero}', author='ServiTech')
    documento.build(flujo)
    return salida.getvalue()
