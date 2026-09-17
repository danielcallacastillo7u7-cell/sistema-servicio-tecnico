from pathlib import Path
import re

from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import obtener_db
from app.models.cliente import Cliente
from app.routes.historial_clientes import router as historial_router

router = APIRouter(prefix="/clientes", tags=["Clientes"])
router.include_router(historial_router)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("")
def listar_clientes(request: Request, db: Session = Depends(obtener_db)):
    clientes = []  # El listado se consulta por AJAX con paginación.
    return templates.TemplateResponse(
        request=request,
        name="clientes.html",
        context={"clientes": clientes, "error": None, "seccion": "clientes"},
    )


@router.post("")
def registrar_cliente(
    request: Request,
    nombres: str = Form(...),
    apellidos: str = Form(...),
    dni_ruc: str = Form(...),
    telefono: str = Form(...),
    db: Session = Depends(obtener_db),
):
    cliente = Cliente(
        nombres=nombres.strip(),
        apellidos=apellidos.strip(),
        dni_ruc=dni_ruc.strip(),
        telefono=telefono.strip(),
    )
    db.add(cliente)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        clientes = db.query(Cliente).order_by(Cliente.id.desc()).all()
        return templates.TemplateResponse(
            request=request,
            name="clientes.html",
            context={
                "clientes": clientes,
                "error": "Ya existe un cliente con ese DNI o RUC.",
                "seccion": "clientes",
            },
            status_code=409,
        )

    return RedirectResponse(url="/clientes", status_code=303)


@router.get("/por-documento/{documento}")
def buscar_por_documento(documento: str, db: Session = Depends(obtener_db)):
    if not re.fullmatch(r"(?:[0-9]{8}|[0-9]{11})", documento):
        raise HTTPException(status_code=400, detail="Ingresa un DNI de 8 dígitos o un RUC de 11.")
    cliente = db.query(Cliente).filter(Cliente.dni_ruc == documento).first()
    if cliente is None:
        return {"encontrado": False}
    return {"encontrado": True, "nombres": cliente.nombres, "apellidos": cliente.apellidos,
            "telefono": cliente.telefono, "dni_ruc": cliente.dni_ruc}
