from app.services.confirmaciones import redireccion_confirmada
from datetime import date
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.services.exportacion_mensual import crear_mensual, tecnicos_disponibles, TIPOS as TIPOS_MENSUALES
from app.database import obtener_db
from app.models.exportacion import HistorialExportacion
from app.models.trabajador import Trabajador
from app.routes.ordenes import ESTADOS_VALIDOS
from app.services.exportaciones import TIPOS_EXPORTACION, crear_excel, obtener_filas, sincronizar_google_sheets

router = APIRouter(prefix="/exportaciones", tags=["Exportaciones"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


def _contexto(db: Session, mensaje: str | None = None, error: str | None = None):
    return {"seccion": "exportaciones", "tipos": {**TIPOS_EXPORTACION, **TIPOS_MENSUALES}, "tecnicos_descarga": tecnicos_disponibles(db), "estados": ESTADOS_VALIDOS, "tecnicos": db.query(Trabajador).filter(Trabajador.activo.is_(True)).order_by(Trabajador.nombre).all(), "historial": db.query(HistorialExportacion).order_by(HistorialExportacion.id.desc()).limit(30).all(), "mensaje": mensaje, "error": error, "hoja_configurada": bool(__import__('os').getenv('GOOGLE_SHEETS_SPREADSHEET_ID'))}


@router.get("")
def ver_exportaciones(request: Request, mensaje: str | None = None, error: str | None = None, db: Session = Depends(obtener_db)):
    return templates.TemplateResponse(request=request, name="exportaciones.html", context=_contexto(db, mensaje, error))


def _filas(db, tipo, fecha_inicio, fecha_fin, estado, tecnico):
    if tipo not in TIPOS_EXPORTACION:
        raise ValueError("Selecciona un tipo de información válido.")
    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")
    if estado and estado not in ESTADOS_VALIDOS:
        raise ValueError("Selecciona un estado válido.")
    return obtener_filas(db, tipo, fecha_inicio, fecha_fin, estado or None, tecnico or None)


@router.post("/excel")
def descargar_excel(tipo: str = Form(...), tecnico: str = Form(""), tecnico2: str = Form(""), db: Session = Depends(obtener_db)):
    try:
        archivo,cantidad,seleccion=crear_mensual(db,tipo,[tecnico,tecnico2])
    except ValueError as exc:
        return RedirectResponse(f"/exportaciones?error={quote(str(exc))}", status_code=303)
    db.add(HistorialExportacion(tipo_informacion=tipo,destino="Excel (.xlsx)",cantidad_registros=cantidad,detalle="Separado por mes; técnicos: "+(', '.join(seleccion) or 'Todos')))
    db.commit()
    return StreamingResponse(archivo,media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",headers={"Content-Disposition":f'attachment; filename="ServiTech-{tipo}-por-mes.xlsx"'})


@router.post("/google-sheets")
def enviar_google_sheets(tipo: str = Form(...), fecha_inicio: date | None = Form(None), fecha_fin: date | None = Form(None), estado: str = Form(""), tecnico: str = Form(""), hoja_referencia: str = Form(""), nombre_hoja: str = Form(""), db: Session = Depends(obtener_db)):
    try:
        filas = _filas(db, tipo, fecha_inicio, fecha_fin, estado, tecnico)
        creados, actualizados = sincronizar_google_sheets(filas, hoja_referencia, nombre_hoja)
        db.add(HistorialExportacion(tipo_informacion=tipo, destino="Google Sheets", cantidad_registros=len(filas), detalle=f"{creados} creados, {actualizados} actualizados por id_orden"))
        db.commit()
        return redireccion_confirmada(f"/exportaciones?mensaje={quote(f'Google Sheets sincronizado: {creados} filas nuevas y {actualizados} actualizadas.')}", "Google Sheets actualizado correctamente.")
    except (ValueError, RuntimeError) as exc:
        db.rollback()
        db.add(HistorialExportacion(tipo_informacion=tipo if tipo in TIPOS_EXPORTACION else "desconocido", destino="Google Sheets", cantidad_registros=0, estado="Error", detalle=str(exc)))
        db.commit()
        return RedirectResponse(f"/exportaciones?error={quote(str(exc))}", status_code=303)


@router.get('/google-sheets/estado')
def estado_sheets():
    from app.services.sheets_automatico import estado
    return estado()

@router.post('/google-sheets/sincronizar')
def solicitar_sheets():
    from app.services.sheets_automatico import solicitar
    solicitar()
    return {'mensaje':'Sincronización solicitada.'}


def proteger_conexiones(request: Request):
    from urllib.parse import urlsplit
    origin=request.headers.get('origin')
    if request.headers.get('x-servitech-config')!='1' or (origin and urlsplit(origin).netloc!=request.headers.get('host')):
        raise HTTPException(403,'Abre la configuración desde ServiTech.')

@router.get('/google-sheets/conexiones')
def listar_conexiones():
    from app.services.sheets_conexiones import listar
    return listar()

@router.post('/google-sheets/conexiones',dependencies=[Depends(proteger_conexiones)])
def agregar_conexion(nombre: str=Form(...), enlace: str=Form(...), archivo: UploadFile=File(...)):
    from app.services.sheets_conexiones import nueva
    from googleapiclient.errors import HttpError
    raw=archivo.file.read(64001)
    try:
        ident=nueva(nombre,enlace,raw)
        return {'id':ident,'mensaje':'Conexión verificada y guardada. Pulsa Activar para iniciar el envío de órdenes.'}
    except ValueError as exc:raise HTTPException(422,str(exc)) from None
    except HttpError as exc:
        raise HTTPException(422,'No se pudo acceder a la hoja. Activa Google Sheets API y comparte la hoja con el correo de la cuenta como Editor.') from None
    except Exception:raise HTTPException(503,'No se pudo verificar la conexión. Revisa internet y vuelve a intentar.') from None
    finally:archivo.file.close()

@router.post('/google-sheets/conexiones/{ident}/activar',dependencies=[Depends(proteger_conexiones)])
def activar_conexion(ident: str):
    from app.services.sheets_conexiones import activar
    from app.services.sheets_automatico import solicitar,informar
    try:activar(ident)
    except ValueError as exc:raise HTTPException(404,str(exc)) from None
    informar(estado='Pendiente',mensaje='Conexión activada. Preparando sincronización…',ultima=None,ordenes=0);solicitar()
    return {'mensaje':'Conexión activada.'}

@router.post('/google-sheets/conexiones/pausar',dependencies=[Depends(proteger_conexiones)])
def pausar_conexion():
    from app.services.sheets_conexiones import activar
    from app.services.sheets_automatico import solicitar,informar
    activar(None);informar(estado='Desactivado',mensaje='Sincronización pausada.',ultima=None,ordenes=0);solicitar()
    return {'mensaje':'Sincronización pausada.'}

@router.delete('/google-sheets/conexiones/{ident}',dependencies=[Depends(proteger_conexiones)])
def eliminar_conexion(ident: str):
    from app.services.sheets_conexiones import quitar
    from app.services.sheets_automatico import solicitar
    try:quitar(ident)
    except ValueError as exc:raise HTTPException(404,str(exc)) from None
    solicitar();return {'mensaje':'Conexión eliminada de ServiTech. La hoja de Google se conserva.'}
