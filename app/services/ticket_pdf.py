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


def generar_ticket_termico_pdf(html, numero):
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


def generar_ticket_pdf(html, numero):
    """Mismo contenido del ticket en una hoja A4 para descargar."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle
    parser = ContenidoTicket(); parser.feed(html)
    normal = ParagraphStyle('a4normal',fontName='Helvetica',fontSize=10,leading=14,spaceAfter=6)
    label = ParagraphStyle('a4label',parent=normal,fontName='Helvetica-Bold',textColor=colors.HexColor('#344054'))
    title = ParagraphStyle('a4title',parent=label,fontSize=14,leading=18,spaceBefore=10,spaceAfter=10)
    flow=[]
    logo=Image(str(Path(__file__).resolve().parents[1]/'static/images/logo-servitech.png'))
    logo.drawHeight *= 40*mm/logo.drawWidth;logo.drawWidth=40*mm
    head=Table([[Paragraph('ORDEN DE RECEPCIÓN<br/>'+escape(numero),title),logo]],colWidths=[125*mm,45*mm])
    head.setStyle(TableStyle([('BACKGROUND',(1,0),(1,0),colors.HexColor('#17212d')),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    flow.extend([head,Spacer(1,6*mm)])
    pending=None
    for tag,text in parser.bloques:
        if tag=='dt':pending=text;continue
        if tag=='dd' and pending:
            row=Table([[Paragraph(escape(pending),label),Paragraph(escape(text),normal)]],colWidths=[45*mm,125*mm])
            row.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(0,0),colors.HexColor('#f3f5f8')),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#dce3ea')),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            flow.append(row);pending=None
        else: flow.append(Paragraph(escape(text),title if tag=='h2' else normal))
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.drawString(20*mm,12*mm,'ServiTech · '+numero);canvas.drawRightString(190*mm,12*mm,str(doc.page))
    out=BytesIO();SimpleDocTemplate(out,pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,topMargin=18*mm,bottomMargin=22*mm,title='Orden '+numero).build(flow,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()
