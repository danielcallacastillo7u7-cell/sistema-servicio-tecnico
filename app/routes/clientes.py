from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import obtener_db
from app.models.cliente import Cliente

router = APIRouter(prefix="/clientes", tags=["Clientes"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("")
def listar_clientes(request: Request, db: Session = Depends(obtener_db)):
    clientes = db.query(Cliente).order_by(Cliente.id.desc()).all()
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
