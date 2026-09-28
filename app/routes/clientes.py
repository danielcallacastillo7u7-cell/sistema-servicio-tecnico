from app.services.confirmaciones import redireccion_confirmada
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

    return redireccion_confirmada("/clientes", "Cliente guardado correctamente.")


@router.get("/por-documento/{documento}")
def buscar_por_documento(documento: str, db: Session = Depends(obtener_db)):
    if not re.fullmatch(r"(?:[0-9]{8}|[0-9]{11})", documento):
        raise HTTPException(status_code=400, detail="Ingresa un DNI de 8 dígitos o un RUC de 11.")
    cliente = db.query(Cliente).filter(Cliente.dni_ruc == documento).first()
    if cliente is None:
        return {"encontrado": False}
    return {"encontrado": True, "nombres": cliente.nombres, "apellidos": cliente.apellidos,
            "telefono": cliente.telefono, "dni_ruc": cliente.dni_ruc}


from pydantic import BaseModel, Field


class DatosEdicionCliente(BaseModel):
    nombres: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    dni_ruc: str = Field(min_length=8, max_length=11)
    telefono: str = Field(min_length=9, max_length=20)


class EdicionCliente(DatosEdicionCliente):
    original: DatosEdicionCliente


@router.put("/api/{cliente_id}")
def editar_cliente(cliente_id: int, datos: EdicionCliente, db: Session = Depends(obtener_db)):
    from app.routes.historial_clientes import datos_cliente
    from app.models.diagnostico import Diagnostico, DiagnosticoMensaje
    from app.models.orden import OrdenServicio
    from app.models.equipo import Equipo
    from app.routes.diagnosticos import crear_mensaje_cliente

    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).with_for_update().first()
    if cliente is None:
        raise HTTPException(404, "Cliente no encontrado.")
    campos = ("nombres", "apellidos", "dni_ruc", "telefono")
    if any(getattr(cliente, campo) != getattr(datos.original, campo) for campo in campos):
        raise HTTPException(409, "El cliente fue modificado desde otra pantalla. Selecciónalo nuevamente antes de guardar.")
    valores = {campo: " ".join(getattr(datos, campo).split()) for campo in campos}
    for campo in ("nombres", "apellidos"):
        if not valores[campo] or not any(c.isalpha() for c in valores[campo]) or not all(c.isalpha() or c in " '-.’" for c in valores[campo]):
            raise HTTPException(422, "Revisa los nombres y apellidos: utiliza letras, espacios, apóstrofos o guiones.")
    if not re.fullmatch(r"(?:[0-9]{8}|[0-9]{11})", valores["dni_ruc"]):
        raise HTTPException(422, "El DNI debe tener 8 dígitos o el RUC 11.")
    if not re.fullmatch(r"[0-9]{9}", valores["telefono"]):
        raise HTTPException(422, "El celular debe tener 9 dígitos.")
    if db.query(Cliente.id).filter(Cliente.dni_ruc == valores["dni_ruc"], Cliente.id != cliente_id).first():
        raise HTTPException(409, "Ya existe otro cliente con ese DNI/RUC. No se han guardado cambios.")
    for campo, valor in valores.items():
        setattr(cliente, campo, valor)
    try:
        pendientes = db.query(Diagnostico).join(Diagnostico.orden).join(OrdenServicio.equipo).join(Diagnostico.mensaje_cliente).filter(Equipo.cliente_id == cliente_id, DiagnosticoMensaje.estado == "Pendiente").all()
        for diagnostico in pendientes:
            diagnostico.mensaje_cliente.mensaje = crear_mensaje_cliente(diagnostico)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "No se pudo guardar: otro cliente utiliza ese DNI/RUC.") from None
    return {"cliente": datos_cliente(cliente), "mensaje": "Cliente actualizado. Ya puedes volver a imprimir sus tickets."}
