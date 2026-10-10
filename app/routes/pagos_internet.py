from pathlib import Path
from uuid import UUID
from decimal import Decimal
from datetime import timezone, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import obtener_db
from app.models.pago_internet import PagoInternet
from app.models.trabajador import Trabajador

router=APIRouter(prefix='/pagos-internet',tags=['Pagos de internet'])
templates=Jinja2Templates(directory=Path(__file__).resolve().parent.parent/'templates')
def fecha_peru(f):
    if f.tzinfo is None: f=f.replace(tzinfo=timezone.utc)
    return f.astimezone(timezone(timedelta(hours=-5))).strftime('%d/%m/%Y %H:%M:%S')
templates.env.filters['pago_fecha']=fecha_peru

class Pago(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    token: UUID
    tecnico_id: int = Field(gt=0)
    periodo: str = Field(pattern=r'^20[0-9]{2}-(0[1-9]|1[0-2])$')
    titular: str = Field(min_length=2,max_length=150)
    dni: str = Field(pattern=r'^[0-9]{8}$')
    direccion: str = Field(min_length=3,max_length=500)
    celular: str = Field(pattern=r'^9[0-9]{8}$')
    observacion: str = Field(default='',max_length=2000)
    subtotal: Decimal | None = Field(default=None,ge=0,max_digits=10,decimal_places=2)
    descuento: Decimal | None = Field(default=None,ge=0,max_digits=10,decimal_places=2)
    total: Decimal = Field(gt=0,max_digits=10,decimal_places=2)
    @model_validator(mode='after')
    def importes(self):
        if self.subtotal is not None and self.subtotal-(self.descuento or Decimal('0')) != self.total:
            raise ValueError('El total debe ser igual al subtotal menos el descuento.')
        return self

@router.get('')
def formulario(request: Request, db: Session=Depends(obtener_db)):
    return templates.TemplateResponse(request=request,name='pagos_internet.html',context=dict(seccion='pagos_internet',tecnicos=db.query(Trabajador).filter_by(activo=True).order_by(Trabajador.nombre).all(),pagos=db.query(PagoInternet).order_by(PagoInternet.id.desc()).limit(50).all()))

@router.post('/api',status_code=201)
def guardar(datos: Pago, db: Session=Depends(obtener_db)):
    contenido=datos.model_dump(mode='json',exclude={'token'})
    token=str(datos.token)
    def respuesta(p):return dict(numero=p.numero,url=f'/pagos-internet/{p.id}/ticket',fecha=fecha_peru(p.fecha))
    previo=db.query(PagoInternet).filter_by(token=token).first()
    if previo:
        if previo.datos!=contenido:raise HTTPException(409,'Este comprobante ya se guardó con otros datos. Abre un nuevo pago.')
        return respuesta(previo)
    tecnico=db.query(Trabajador).filter_by(id=datos.tecnico_id,activo=True).first()
    if not tecnico:raise HTTPException(422,'Selecciona un técnico activo.')
    pago=PagoInternet(token=token,emisor=tecnico.nombre,datos=contenido);db.add(pago)
    try:db.commit()
    except IntegrityError:
        db.rollback();previo=db.query(PagoInternet).filter_by(token=token).first()
        if previo and previo.datos==contenido:return respuesta(previo)
        raise HTTPException(409,'No se pudo guardar el comprobante.')
    return respuesta(pago)

@router.get('/{ident}/ticket')
def ticket(ident:int,request:Request,db:Session=Depends(obtener_db)):
    pago=db.get(PagoInternet,ident)
    if not pago:raise HTTPException(404,'Comprobante no encontrado')
    meses=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
    return templates.TemplateResponse(request=request,name='pago_internet_ticket.html',context=dict(pago=pago,d=pago.datos,periodo=meses[int(pago.datos['periodo'][5:])-1]+' '+pago.datos['periodo'][:4]),headers={'Cache-Control':'no-store'})


@router.get('/{ident}/pdf')
def descargar_pdf(ident: int, db: Session = Depends(obtener_db)):
    from fastapi.responses import Response
    from app.services.pago_internet_pdf import generar_pdf_pago
    pago = db.get(PagoInternet, ident)
    if not pago:
        raise HTTPException(404, 'Comprobante no encontrado')
    return Response(generar_pdf_pago(pago, fecha_peru(pago.fecha)), media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="{pago.numero}-A4.pdf"', 'Cache-Control': 'no-store'})
