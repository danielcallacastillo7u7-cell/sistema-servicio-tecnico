from datetime import datetime, timezone
from decimal import Decimal
import hmac, os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy.orm import Session
from app.database import obtener_db
from app.models.bloqueo_cliente import BloqueoCliente
from app.services.morosidad import bloqueo_activo
router=APIRouter(prefix='/morosidad',tags=['Morosidad'])
class RegistroBloqueo(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')
    documento:str=Field(pattern=r'^(?:[0-9]{8}|[0-9]{11})$')
    nombre:str=Field(min_length=2,max_length=200)
    motivo:str=Field(min_length=3,max_length=1000)
    monto:Decimal|None=Field(default=None,ge=0,max_digits=12,decimal_places=2)
class Desbloqueo(BaseModel):
    clave:str=Field(min_length=1,max_length=200)
@router.get('/api')
def listar(db:Session=Depends(obtener_db)):
    return [dict(id=x.id,documento=x.documento,nombre=x.nombre,motivo=x.motivo,monto=str(x.monto) if x.monto is not None else None,fecha=x.fecha.isoformat()) for x in db.query(BloqueoCliente).filter_by(activo=True).order_by(BloqueoCliente.id.desc()).all()]
@router.post('/api',status_code=201)
def bloquear(datos:RegistroBloqueo,db:Session=Depends(obtener_db)):
    if bloqueo_activo(db,datos.documento):raise HTTPException(409,'Este documento ya tiene un bloqueo activo.')
    item=BloqueoCliente(**datos.model_dump());db.add(item);db.commit();return {'ok':True}
@router.post('/api/{id}/desbloquear')
def desbloquear(id:int,datos:Desbloqueo,db:Session=Depends(obtener_db)):
    expected=os.getenv('CLAVE_DESBLOQUEO_MOROSIDAD','SERVITECH2026')
    if not hmac.compare_digest(datos.clave.encode(),expected.encode()):raise HTTPException(403,'Contraseña incorrecta.')
    item=db.query(BloqueoCliente).filter_by(id=id,activo=True).first()
    if not item:raise HTTPException(404,'El bloqueo no existe o ya fue levantado.')
    item.activo=False;item.desbloqueado=datetime.now(timezone.utc);db.commit();return {'ok':True}


@router.get('/detalle/{documento}')
def detalle(documento:str,db:Session=Depends(obtener_db)):
    from app.models.orden import OrdenServicio
    from app.models.equipo import Equipo
    from app.models.cliente import Cliente
    item=bloqueo_activo(db,documento)
    if not item:raise HTTPException(404,'Este documento no tiene un bloqueo activo.')
    cliente=db.query(Cliente).filter_by(dni_ruc=documento).first()
    ordenes=db.query(OrdenServicio).join(Equipo,OrdenServicio.equipo_id==Equipo.id).join(Cliente,Equipo.cliente_id==Cliente.id).filter(Cliente.dni_ruc==documento).order_by(OrdenServicio.id.desc()).all()
    return {'id':item.id,'documento':item.documento,'nombre':item.nombre,'telefono':cliente.telefono if cliente else None,'motivo':item.motivo,'monto':str(item.monto) if item.monto is not None else None,'fecha':item.fecha.isoformat(),'ordenes':[{'numero':x.numero_orden,'estado':x.estado,'equipo':' '.join(str(v) for v in [x.equipo.tipo,x.equipo.marca,x.equipo.modelo] if v),'ticket':'/ordenes?ticket='+str(x.id)} for x in ordenes]}
