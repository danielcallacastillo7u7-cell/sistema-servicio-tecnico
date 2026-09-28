from html import escape
from io import BytesIO
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image


def generar_instalacion_pdf(registro, fecha):
    out = BytesIO()
    styles = getSampleStyleSheet()
    styles['BodyText'].fontSize = 10
    styles['BodyText'].leading = 14
    def p(value):
        return Paragraph(escape(str(value)).replace('\n','<br/>'), styles['BodyText'])
    logo = Image(str(Path(__file__).resolve().parents[1] / 'static/images/logo-seguritech.png'))
    logo.drawHeight *= (38*mm)/logo.drawWidth
    logo.drawWidth = 38*mm
    heading = Table([[Paragraph('Reporte de instalación',styles['Title']),logo]], colWidths=[127*mm,43*mm])
    heading.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BACKGROUND',(1,0),(1,0),colors.HexColor('#000000'))]))
    flow = [heading,Spacer(1,6*mm),p('Registro: '+registro.numero),p('Fecha de registro: '+fecha+' (Perú)'),p('Fecha programada: '+registro.fecha_instalacion.strftime('%d/%m/%Y'))]
    d = registro.datos
    def section(title, text=None):
        flow.extend([Spacer(1,4*mm),Paragraph(title,styles['Heading2'])])
        if text is not None: flow.append(p(text))
    def table(headers, rows, widths):
        t = Table([[p(x) for x in headers]]+[[p(x) for x in row] for row in rows],colWidths=[x*mm for x in widths],repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eef2f6')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#dce2e8')),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        flow.append(t)
    section('Datos del cliente',d['nombres']+' '+d['apellidos'])
    flow.extend([p('DNI/RUC: '+d['dni_ruc']+' · Celular: '+d['celular']),p('Responsable técnico: '+registro.tecnico)])
    section('Dirección de instalación',d['direccion'])
    section('Cámaras')
    table(['Modelo','Procedencia','Cantidad'],[[x['modelo'] or 'Sin especificar',{'ServiTech':'Vendida por ServiTech','Cliente':'Aportada por el cliente'}.get(x['procedencia'],'Sin especificar'),x['cantidad'] if x['cantidad'] is not None else 'Sin especificar'] for x in d['camaras']],[65,75,30])
    section('Otro producto o servicio',d.get('otro_producto_servicio') or 'No especificado')
    section('Servicio técnico a domicilio',{'si':'Sí','no':'No'}.get(d.get('servicio_domicilio'),'Sin especificar'))
    section('Productos vendidos (detalle)',d['observaciones'] or 'No especificados.')
    section('Productos vendidos')
    if d['productos']:
        table(['Producto','Cantidad','Unidad'],[[x['descripcion'],x['cantidad'],x['unidad']] for x in d['productos']],[100,35,35])
    else: flow.append(p('No se registraron productos adicionales vendidos.'))
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#667085'));canvas.drawString(20*mm,12*mm,'SeguriTech · '+registro.numero);canvas.drawRightString(190*mm,12*mm,str(doc.page))
    SimpleDocTemplate(out,pagesize=A4,rightMargin=20*mm,leftMargin=20*mm,topMargin=18*mm,bottomMargin=22*mm,title='Instalación '+registro.numero).build(flow,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()
