from pathlib import Path

import re
import hmac
import os

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import obtener_db
from app.models.cancelacion import CancelacionOrden
from app.models.equipo import Equipo
from app.models.orden import OrdenServicio
from app.models.trabajador import Trabajador

router = APIRouter(prefix="/ajustes", tags=["Ajustes"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)
CLAVE_ELIMINACION = os.getenv("CLAVE_ELIMINACION", "SERVITECH2026")


def contexto_ajustes(db: Session, error: str | None = None):
    cancelaciones = (
        db.query(CancelacionOrden)
        .options(
            joinedload(CancelacionOrden.orden)
            .joinedload(OrdenServicio.equipo)
            .joinedload(Equipo.cliente)
        )
        .order_by(CancelacionOrden.id.desc())
        .all()
    )
    trabajadores = (
        db.query(Trabajador)
        .filter(Trabajador.activo.is_(True))
        .order_by(Trabajador.nombre)
        .all()
    )
    return {
        "seccion": "ajustes",
        "cancelaciones": cancelaciones,
        "trabajadores": trabajadores,
        "error": error,
    }


@router.get("")
def ver_ajustes(request: Request, db: Session = Depends(obtener_db)):
    return templates.TemplateResponse(
        request=request,
        name="ajustes.html",
        context=contexto_ajustes(db),
    )


@router.post("/trabajadores")
def agregar_trabajador(
    request: Request,
    nombre: str = Form(...),
    db: Session = Depends(obtener_db),
):
    nombre = " ".join(nombre.split())
    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,120}", nombre):
        return templates.TemplateResponse(
            request=request,
            name="ajustes.html",
            context=contexto_ajustes(db, "El nombre del trabajador solo puede contener letras y espacios."),
            status_code=400,
        )

    existente = db.query(Trabajador).filter(Trabajador.nombre.ilike(nombre)).first()
    if existente:
        existente.activo = True
    else:
        db.add(Trabajador(nombre=nombre))
    db.commit()

    return RedirectResponse(url="/ajustes", status_code=303)


@router.post("/trabajadores/{trabajador_id}/eliminar")
def eliminar_trabajador(
    trabajador_id: int,
    request: Request,
    clave: str = Form(...),
    db: Session = Depends(obtener_db),
):
    if not hmac.compare_digest(clave, CLAVE_ELIMINACION):
        return templates.TemplateResponse(
            request=request,
            name="ajustes.html",
            context=contexto_ajustes(db, "La clave de eliminación es incorrecta."),
            status_code=403,
        )

    trabajador = db.get(Trabajador, trabajador_id)
    if trabajador is None:
        return templates.TemplateResponse(
            request=request,
            name="ajustes.html",
            context=contexto_ajustes(db, "El trabajador ya no existe."),
            status_code=404,
        )

    db.delete(trabajador)
    db.commit()
    return RedirectResponse(url="/ajustes", status_code=303)
