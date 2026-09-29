from io import BytesIO
from html import escape
from decimal import Decimal
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether


def generar_pdf_pago(pago, fecha):
    out = BytesIO()
    ink = colors.HexColor('#162D3A')
    accent = colors.HexColor('#147D92')
    muted = colors.HexColor('#617581')
    pale = colors.HexColor('#F0F5F7')
    width = 174*mm
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=17*mm, bottomMargin=20*mm, title=f'{pago.numero} - Comprobante de internet', author='ServiTel')
    def para(text, size=11, color=ink, bold=False, **kw):
        return Paragraph(text, ParagraphStyle('p', fontName='Helvetica-Bold' if bold else 'Helvetica', fontSize=size, leading=size*1.4, textColor=color, **kw))
    def value(v): return escape(str(v)).replace('\n','<br/>')
    def field(label, v):
        return [para(label.upper(), 8, muted, True), Spacer(1,3), para(value(v), 11)]
    def box(rows, widths):
        t=Table(rows, colWidths=widths, hAlign='LEFT')
        t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),11),('BOTTOMPADDING',(0,0),(-1,-1),11),('BACKGROUND',(0,0),(-1,-1),pale),('LINEBELOW',(0,0),(-1,-2),.5,colors.white)]))
        return t
    logo=Path(__file__).resolve().parent.parent/'static/images/logo-servitel.png'
    head=Table([[Image(str(logo),width=31*mm,height=31*mm),[para('COMPROBANTE DE PAGO',19,ink,True),para('Servicio de internet',12,muted),Spacer(1,8),para(pago.numero,13,accent,True)]]],colWidths=[42*mm,132*mm])
    head.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0),('LINEBELOW',(0,0),(-1,-1),2,accent),('BOTTOMPADDING',(0,0),(-1,-1),12)]))
    d=pago.datos
    months=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
    periodo=months[int(d['periodo'][5:])-1]+' '+d['periodo'][:4]
    story=[head,Spacer(1,16),box([[field('Fecha y hora de emisión · Perú',fecha),field('Emitido por',pago.emisor)]],[width/2,width/2]),Spacer(1,20),para('DATOS DEL TITULAR',10,accent,True),Spacer(1,8),box([[field('Nombre del titular',d['titular']),field('DNI',d['dni'])],[field('Dirección',d['direccion']),field('Celular',d['celular'])]],[width*.64,width*.36]),Spacer(1,20),para('DETALLE DEL PAGO',10,accent,True),Spacer(1,8)]
    detail=Table([[para('CONCEPTO',8,muted,True),para('MES PAGADO',8,muted,True)],[para('Pago del servicio de internet',11),para(periodo,11,bold=True)]],colWidths=[width*.64,width*.36])
    detail.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),('BACKGROUND',(0,0),(-1,0),pale),('LINEBELOW',(0,1),(-1,1),.5,colors.HexColor('#D8E2E7'))]))
    story.extend([detail,Spacer(1,12)])
    total=Table([[para('TOTAL DEL PAGO',10,colors.white,True),para('S/ '+format(Decimal(d['total']),'.2f'),24,colors.white,True,alignment=2)]],colWidths=[width*.55,width*.45])
    total.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),ink),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),16),('RIGHTPADDING',(0,0),(-1,-1),16),('TOPPADDING',(0,0),(-1,-1),14),('BOTTOMPADDING',(0,0),(-1,-1),14)]))
    story.append(total)
    if d.get('observacion'):
        story.extend([Spacer(1,16),para('OBSERVACIÓN',9,muted,True),Spacer(1,5),para(value(d['observacion']),10)])
    story.extend([Spacer(1,20),KeepTogether([para('REGISTRO DE TU PAGO',9,accent,True,alignment=1),Spacer(1,6),para('Una vez cancelado, envía una captura de este comprobante al WhatsApp',10,alignment=1),para('922 048 201',22,ink,True,alignment=1),para('para su registro correspondiente.',10,muted,alignment=1)])])
    def footer(canvas, doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#D8E2E7'));canvas.line(18*mm,15*mm,192*mm,15*mm);canvas.setFont('Helvetica',8);canvas.setFillColor(muted);canvas.drawString(18*mm,10*mm,'ServiTel | Comprobante de pago de internet');canvas.drawRightString(192*mm,10*mm,f'{pago.numero}  /  {doc.page}');canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()
