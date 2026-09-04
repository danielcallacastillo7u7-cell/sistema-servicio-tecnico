from datetime import date
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import obtener_db
from app.models.exportacion import HistorialExportacion
from app.models.trabajador import Trabajador
from app.routes.ordenes import ESTADOS_VALIDOS
from app.services.exportaciones import TIPOS_EXPORTACION, crear_excel, obtener_filas, sincronizar_google_sheets

router = APIRouter(prefix="/exportaciones", tags=["Exportaciones"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


def _contexto(db: Session, mensaje: str | None = None, error: str | None = None):
    return {"seccion": "exportaciones", "tipos": TIPOS_EXPORTACION, "estados": ESTADOS_VALIDOS, "tecnicos": db.query(Trabajador).filter(Trabajador.activo.is_(True)).order_by(Trabajador.nombre).all(), "historial": db.query(HistorialExportacion).order_by(HistorialExportacion.id.desc()).limit(30).all(), "mensaje": mensaje, "error": error}


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
def descargar_excel(tipo: str = Form(...), fecha_inicio: date | None = Form(None), fecha_fin: date | None = Form(None), estado: str = Form(""), tecnico: str = Form(""), db: Session = Depends(obtener_db)):
    try:
        filas = _filas(db, tipo, fecha_inicio, fecha_fin, estado, tecnico)
    except ValueError as exc:
        return RedirectResponse(f"/exportaciones?error={quote(str(exc))}", status_code=303)
    db.add(HistorialExportacion(tipo_informacion=tipo, destino="Excel (.xlsx)", cantidad_registros=len(filas), detalle=f"Filtros: {fecha_inicio or 'sin inicio'} a {fecha_fin or 'sin fin'}; estado={estado or 'todos'}; técnico={tecnico or 'todos'}"))
    db.commit()
    nombre = f"servitech_{tipo}_{date.today().isoformat()}.xlsx"
    return StreamingResponse(crear_excel(filas, TIPOS_EXPORTACION[tipo]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@router.post("/google-sheets")
def enviar_google_sheets(tipo: str = Form(...), fecha_inicio: date | None = Form(None), fecha_fin: date | None = Form(None), estado: str = Form(""), tecnico: str = Form(""), db: Session = Depends(obtener_db)):
    try:
        filas = _filas(db, tipo, fecha_inicio, fecha_fin, estado, tecnico)
        creados, actualizados = sincronizar_google_sheets(filas)
        db.add(HistorialExportacion(tipo_informacion=tipo, destino="Google Sheets", cantidad_registros=len(filas), detalle=f"{creados} creados, {actualizados} actualizados por id_orden"))
        db.commit()
        return RedirectResponse(f"/exportaciones?mensaje={quote(f'Google Sheets sincronizado: {creados} filas nuevas y {actualizados} actualizadas.')}", status_code=303)
    except (ValueError, RuntimeError) as exc:
        db.rollback()
        db.add(HistorialExportacion(tipo_informacion=tipo if tipo in TIPOS_EXPORTACION else "desconocido", destino="Google Sheets", cantidad_registros=0, estado="Error", detalle=str(exc)))
        db.commit()
        return RedirectResponse(f"/exportaciones?error={quote(str(exc))}", status_code=303)
