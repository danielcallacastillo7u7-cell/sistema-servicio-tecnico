from pathlib import Path
from decimal import Decimal
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from app.database import obtener_db
from app.models.insumo import Insumo, MovimientoInsumo, OpcionInventario
from sqlalchemy.exc import IntegrityError
from typing import Literal

router = APIRouter(prefix='/inventario', tags=['Inventario'])
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent/'templates')
CATEGORIAS = ['Refrigeración', 'Limpieza', 'Soldadura', 'Impresión', 'Repuestos', 'Cables y conectores', 'Otros']
UNIDADES = ['und', 'g', 'kg', 'ml', 'litros', 'metros', 'rollo', 'cajas']
class DatosInsumo(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    nombre: str = Field(min_length=1, max_length=150)
    categoria: str = Field(min_length=1, max_length=80)
    marca: str = Field(default='', max_length=100)
    unidad: str = Field(min_length=1, max_length=40)
    cantidad: Decimal = Field(ge=0, max_digits=14, decimal_places=3)
    stock_minimo: Decimal = Field(default=Decimal('0'), ge=0, max_digits=14, decimal_places=3)
    precio: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    descripcion: str = Field(default='', max_length=2000)
class AjusteStock(BaseModel):
    cantidad: Decimal = Field( max_digits=14, decimal_places=3)
    motivo: str = Field(min_length=1, max_length=250)
def serialize(item):
    estado = 'Agotado' if item.cantidad == 0 else 'Stock bajo' if item.cantidad <= 2 else 'Disponible'
    return dict(id=item.id, nombre=item.nombre,categoria=item.categoria,marca=item.marca,unidad=item.unidad,cantidad=str(item.cantidad),stock_minimo=str(item.stock_minimo),precio=str(item.precio) if item.precio is not None else None,descripcion=item.descripcion,estado=estado)
def buscar(db, id):
    item=db.query(Insumo).filter(Insumo.id==id, Insumo.activo.is_(True)).with_for_update().first()
    if item is None: raise HTTPException(404,'El insumo no existe.')
    return item
def opciones(db, tipo):
    base = CATEGORIAS if tipo == 'categoria' else UNIDADES
    return base + [x.nombre for x in db.query(OpcionInventario).filter_by(tipo=tipo).order_by(OpcionInventario.nombre).all() if x.nombre not in base]

def validar(datos, db):
    if datos.categoria not in opciones(db, 'categoria') or datos.unidad not in opciones(db, 'unidad'): raise HTTPException(422,'Selecciona una categoría y unidad válidas.')
@router.get('')
def pantalla(request: Request):
    return templates.TemplateResponse(request=request,name='inventario.html',context={'seccion':'inventario'})
@router.get('/api')
def listado(db: Session=Depends(obtener_db)):
    return {'insumos':[serialize(i) for i in db.query(Insumo).filter(Insumo.activo.is_(True)).order_by(Insumo.id.desc()).all()], 'categorias':opciones(db, 'categoria'),'unidades':opciones(db, 'unidad')}
@router.post('/api',status_code=201)
def crear(datos: DatosInsumo,db: Session=Depends(obtener_db)):
    validar(datos, db)
    item=Insumo(**datos.model_dump());db.add(item);db.flush()
    db.add(MovimientoInsumo(insumo_id=item.id,cantidad=item.cantidad,saldo=item.cantidad,motivo='Registro inicial'))
    db.commit();db.refresh(item);return serialize(item)
@router.put('/api/{id}')
def editar(id:int,datos:DatosInsumo,db:Session=Depends(obtener_db)):
    validar(datos, db);item=buscar(db,id);delta=datos.cantidad-item.cantidad
    for key,value in datos.model_dump().items(): setattr(item,key,value)
    if delta: db.add(MovimientoInsumo(insumo_id=id,cantidad=delta,saldo=item.cantidad,motivo='Corrección al editar'))
    db.commit();db.refresh(item);return serialize(item)
@router.post('/api/{id}/stock')
def stock(id:int,datos:AjusteStock,db:Session=Depends(obtener_db)):
    if datos.cantidad == 0: raise HTTPException(422,'La cantidad debe ser mayor que cero.')
    item=buscar(db,id)
    if item.cantidad+datos.cantidad<0: raise HTTPException(409,'No hay stock suficiente para descontar esa cantidad.')
    item.cantidad+=datos.cantidad
    db.add(MovimientoInsumo(insumo_id=id,cantidad=datos.cantidad,saldo=item.cantidad,motivo=datos.motivo))
    db.commit();db.refresh(item);return serialize(item)
@router.delete('/api/{id}')
def eliminar(id:int,db:Session=Depends(obtener_db)):
    item=buscar(db,id);item.activo=False;db.commit();return {'ok':True}


class NuevaOpcion(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    nombre: str = Field(min_length=1, max_length=80)

@router.post('/opciones/{tipo}', status_code=201)
def agregar_opcion(tipo: Literal['categoria', 'unidad'], datos: NuevaOpcion, db: Session=Depends(obtener_db)):
    nombre = ' '.join(datos.nombre.split())
    if not nombre or (tipo == 'unidad' and len(nombre) > 40):
        raise HTTPException(422, 'Revisa el nombre: la unidad admite hasta 40 caracteres.')
    existente = next((v for v in opciones(db, tipo) if v.casefold() == nombre.casefold()), None)
    if existente: return {'nombre': existente, 'opciones': opciones(db, tipo)}
    item = OpcionInventario(tipo=tipo, nombre=nombre, clave=tipo+':'+nombre.casefold())
    db.add(item)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        item = db.query(OpcionInventario).filter_by(clave=tipo+':'+nombre.casefold()).one()
    return {'nombre': item.nombre, 'opciones': opciones(db, tipo)}
