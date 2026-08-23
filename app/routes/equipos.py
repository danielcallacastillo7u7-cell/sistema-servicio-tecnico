from pathlib import Path
import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import obtener_db
from app.models.cliente import Cliente
from app.models.equipo import Equipo

router = APIRouter(prefix="/equipos", tags=["Equipos"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def contexto_equipos(db: Session, error: str | None = None):
    clientes = db.query(Cliente).order_by(Cliente.nombres, Cliente.apellidos).all()
    equipos = (
        db.query(Equipo)
        .options(joinedload(Equipo.cliente))
        .order_by(Equipo.id.desc())
        .all()
    )
    return {
        "clientes": clientes,
        "equipos": equipos,
        "error": error,
        "seccion": "equipos",
    }


@router.get("")
def listar_equipos(request: Request, db: Session = Depends(obtener_db)):
    return templates.TemplateResponse(
        request=request,
        name="equipos.html",
        context=contexto_equipos(db),
    )


@router.post("")
def registrar_equipo(
    request: Request,
    nombres: str = Form(...),
    apellidos: str = Form(...),
    dni_ruc: str = Form(...),
    telefono: str = Form(...),
    tipo: str = Form(...),
    tipo_otro: str = Form(""),
    marca: str = Form(""),
    modelo: str = Form(...),
    numero_serie: str = Form(""),
    accesorio_opcion: str = Form(...),
    accesorios_detalle: str = Form(""),
    observaciones: str = Form(""),
    db: Session = Depends(obtener_db),
):
    nombres = " ".join(nombres.split())
    apellidos = " ".join(apellidos.split())
    dni_ruc = dni_ruc.strip()
    telefono = telefono.strip()

    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,100}", nombres):
        return templates.TemplateResponse(
            request=request,
            name="equipos.html",
            context=contexto_equipos(db, "Los nombres solo pueden contener letras y espacios."),
            status_code=400,
        )
    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,100}", apellidos):
        return templates.TemplateResponse(
            request=request,
            name="equipos.html",
            context=contexto_equipos(db, "Los apellidos solo pueden contener letras y espacios."),
            status_code=400,
        )
    if not re.fullmatch(r"(?:\d{8}|\d{11})", dni_ruc):
        return templates.TemplateResponse(
            request=request,
            name="equipos.html",
            context=contexto_equipos(db, "El DNI debe tener 8 dígitos o el RUC 11 dígitos."),
            status_code=400,
        )
    if not re.fullmatch(r"9\d{8}", telefono):
        return templates.TemplateResponse(
            request=request,
            name="equipos.html",
            context=contexto_equipos(db, "El celular peruano debe comenzar con 9 y tener 9 dígitos."),
            status_code=400,
        )

    tipos_validos = {"Laptop", "Impresora", "CPU", "Otro"}
    if tipo not in tipos_validos:
        return templates.TemplateResponse(
            request=request,
            name="equipos.html",
            context=contexto_equipos(db, "Selecciona un tipo de equipo válido."),
            status_code=400,
        )
    if tipo == "Otro":
        tipo = tipo_otro.strip()
        if not tipo:
            return templates.TemplateResponse(
                request=request,
                name="equipos.html",
                context=contexto_equipos(db, "Especifica el tipo de equipo."),
                status_code=400,
            )

    modelo = modelo.strip()
    if not modelo:
        return templates.TemplateResponse(
            request=request,
            name="equipos.html",
            context=contexto_equipos(db, "El modelo del equipo es obligatorio."),
            status_code=400,
        )

    if accesorio_opcion == "Ninguno":
        accesorios = "Ninguno"
    elif accesorio_opcion == "Especificar" and accesorios_detalle.strip():
        accesorios = accesorios_detalle.strip()
    else:
        return templates.TemplateResponse(
            request=request,
            name="equipos.html",
            context=contexto_equipos(db, "Indica si el equipo llegó sin accesorios o especifica cuáles."),
            status_code=400,
        )

    cliente = db.query(Cliente).filter(Cliente.dni_ruc == dni_ruc).first()

    if cliente is None:
        cliente = Cliente(
            nombres=nombres,
            apellidos=apellidos,
            dni_ruc=dni_ruc,
            telefono=telefono,
        )
        db.add(cliente)
        db.flush()
    else:
        cliente.nombres = nombres
        cliente.apellidos = apellidos
        cliente.telefono = telefono

    equipo = Equipo(
        cliente_id=cliente.id,
        tipo=tipo.strip(),
        marca=marca.strip() or "Sin especificar",
        modelo=modelo,
        numero_serie=numero_serie.strip() or None,
        accesorios=accesorios,
        observaciones=observaciones.strip() or None,
    )
    db.add(equipo)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="equipos.html",
            context=contexto_equipos(db, "Ya existe un equipo con ese número de serie."),
            status_code=409,
        )

    return RedirectResponse(url="/equipos", status_code=303)
