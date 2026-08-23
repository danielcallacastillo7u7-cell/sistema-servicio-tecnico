from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import obtener_db
from app.models.diagnostico import Diagnostico
from app.models.equipo import Equipo
from app.models.orden import OrdenServicio

router = APIRouter(prefix="/diagnosticos", tags=["Diagnósticos"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def contexto_diagnosticos(db: Session, error: str | None = None):
    ordenes_pendientes = (
        db.query(OrdenServicio)
        .options(joinedload(OrdenServicio.equipo).joinedload(Equipo.cliente))
        .filter(OrdenServicio.diagnostico == None)  # noqa: E711
        .order_by(OrdenServicio.id.desc())
        .all()
    )
    diagnosticos = (
        db.query(Diagnostico)
        .options(
            joinedload(Diagnostico.orden)
            .joinedload(OrdenServicio.equipo)
            .joinedload(Equipo.cliente)
        )
        .order_by(Diagnostico.id.desc())
        .all()
    )
    return {
        "ordenes_pendientes": ordenes_pendientes,
        "diagnosticos": diagnosticos,
        "error": error,
        "seccion": "diagnosticos",
    }


@router.get("")
def listar_diagnosticos(request: Request, db: Session = Depends(obtener_db)):
    return templates.TemplateResponse(
        request=request,
        name="diagnosticos.html",
        context=contexto_diagnosticos(db),
    )


@router.post("")
def registrar_diagnostico(
    request: Request,
    orden_id: int = Form(...),
    falla_encontrada: str = Form(...),
    solucion_recomendada: str = Form(...),
    repuestos_necesarios: str = Form(""),
    costo_estimado: str = Form("0"),
    db: Session = Depends(obtener_db),
):
    orden = db.get(OrdenServicio, orden_id)
    if orden is None or orden.diagnostico is not None:
        return templates.TemplateResponse(
            request=request,
            name="diagnosticos.html",
            context=contexto_diagnosticos(db, "Selecciona una orden pendiente válida."),
            status_code=400,
        )

    try:
        costo = Decimal(costo_estimado.strip() or "0")
        if costo < 0:
            raise InvalidOperation
    except InvalidOperation:
        return templates.TemplateResponse(
            request=request,
            name="diagnosticos.html",
            context=contexto_diagnosticos(db, "Ingresa un costo válido."),
            status_code=400,
        )

    diagnostico = Diagnostico(
        orden_id=orden_id,
        falla_encontrada=falla_encontrada.strip(),
        solucion_recomendada=solucion_recomendada.strip(),
        repuestos_necesarios=repuestos_necesarios.strip() or None,
        costo_estimado=costo,
    )
    orden.estado = "Diagnosticado"
    db.add(diagnostico)
    db.commit()

    return RedirectResponse(url="/diagnosticos", status_code=303)
