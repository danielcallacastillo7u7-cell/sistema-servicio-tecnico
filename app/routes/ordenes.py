from datetime import datetime
from pathlib import Path
import hmac
import os
import re

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import obtener_db
from app.models.cancelacion import CancelacionOrden
from app.models.cliente import Cliente
from app.models.diagnostico import Diagnostico
from app.models.equipo import Equipo
from app.models.historial import HistorialEstado
from app.models.orden import OrdenServicio
from app.models.trabajador import Trabajador

router = APIRouter(prefix="/ordenes", tags=["Órdenes"])

ESTADOS_VALIDOS = (
    "Recibido",
    "Diagnosticado",
    "Esperando aprobación",
    "En reparación",
    "Listo para entrega",
    "Entregado",
    "No reparable",
    "Cancelado",
)

MOTIVOS_CANCELACION = (
    "El cliente ya no desea el servicio",
    "No aprobó el presupuesto",
    "Retiró el equipo",
    "Registro duplicado",
    "Otro motivo",
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)
CLAVE_ELIMINACION = os.getenv("CLAVE_ELIMINACION", "SERVITECH2026")


def contexto_ordenes(
    db: Session,
    error: str | None = None,
    ticket_id: int | None = None,
):
    ordenes = (
        db.query(OrdenServicio)
        .options(joinedload(OrdenServicio.equipo).joinedload(Equipo.cliente))
        .order_by(OrdenServicio.id.desc())
        .all()
    )
    trabajadores = (
        db.query(Trabajador)
        .filter(Trabajador.activo.is_(True))
        .order_by(Trabajador.nombre)
        .all()
    )
    ticket_orden = None
    if ticket_id is not None:
        ticket_orden = (
            db.query(OrdenServicio)
            .options(joinedload(OrdenServicio.equipo).joinedload(Equipo.cliente))
            .filter(OrdenServicio.id == ticket_id)
            .first()
        )
    return {
        "ordenes": ordenes,
        "error": error,
        "seccion": "ordenes",
        "estados_validos": ESTADOS_VALIDOS,
        "motivos_cancelacion": MOTIVOS_CANCELACION,
        "trabajadores": trabajadores,
        "ticket_orden": ticket_orden,
    }


@router.get("")
def listar_ordenes(
    request: Request,
    ticket: int | None = Query(default=None),
    db: Session = Depends(obtener_db),
):
    return templates.TemplateResponse(
        request=request,
        name="ordenes.html",
        context=contexto_ordenes(db, ticket_id=ticket),
    )


@router.post("")
def registrar_orden(
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
    falla_reportada: str = Form(...),
    tecnico_responsable: str = Form(...),
    db: Session = Depends(obtener_db),
):
    nombres = " ".join(nombres.split())
    apellidos = " ".join(apellidos.split())
    dni_ruc = dni_ruc.strip()
    telefono = telefono.strip()
    modelo = modelo.strip()
    numero_serie = numero_serie.strip()

    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,100}", nombres):
        mensaje = "Los nombres solo pueden contener letras y espacios."
    elif not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,100}", apellidos):
        mensaje = "Los apellidos solo pueden contener letras y espacios."
    elif not re.fullmatch(r"(?:\d{8}|\d{11})", dni_ruc):
        mensaje = "El DNI debe tener 8 dígitos o el RUC 11 dígitos."
    elif not re.fullmatch(r"9\d{8}", telefono):
        mensaje = "El celular peruano debe comenzar con 9 y tener 9 dígitos."
    elif tipo not in {"Laptop", "Impresora", "CPU", "Otro"}:
        mensaje = "Selecciona un tipo de equipo válido."
    elif tipo == "Otro" and not tipo_otro.strip():
        mensaje = "Especifica el tipo de equipo."
    elif not modelo:
        mensaje = "El modelo del equipo es obligatorio."
    elif not falla_reportada.strip():
        mensaje = "La falla indicada por el cliente es obligatoria."
    elif not db.query(Trabajador).filter(
        Trabajador.nombre == tecnico_responsable,
        Trabajador.activo.is_(True),
    ).first():
        mensaje = "Selecciona un técnico responsable registrado."
    else:
        mensaje = None

    if mensaje:
        return templates.TemplateResponse(
            request=request,
            name="ordenes.html",
            context=contexto_ordenes(db, mensaje),
            status_code=400,
        )

    tipo_final = tipo_otro.strip() if tipo == "Otro" else tipo
    if accesorio_opcion == "Ninguno":
        accesorios = "Ninguno"
    elif accesorio_opcion == "Especificar" and accesorios_detalle.strip():
        accesorios = accesorios_detalle.strip()
    else:
        return templates.TemplateResponse(
            request=request,
            name="ordenes.html",
            context=contexto_ordenes(db, "Indica los accesorios entregados o selecciona Ninguno."),
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

    equipo = None
    if numero_serie:
        equipo = db.query(Equipo).filter(Equipo.numero_serie == numero_serie).first()
        if equipo is not None and equipo.cliente_id != cliente.id:
            db.rollback()
            return templates.TemplateResponse(
                request=request,
                name="ordenes.html",
                context=contexto_ordenes(db, "Ese número de serie pertenece a otro cliente."),
                status_code=409,
            )

    if equipo is None:
        equipo = Equipo(
            cliente_id=cliente.id,
            tipo=tipo_final,
            marca=marca.strip() or "Sin especificar",
            modelo=modelo,
            numero_serie=numero_serie or None,
            accesorios=accesorios,
            observaciones=observaciones.strip() or None,
        )
        db.add(equipo)
        db.flush()
    else:
        equipo.tipo = tipo_final
        equipo.marca = marca.strip() or "Sin especificar"
        equipo.modelo = modelo
        equipo.accesorios = accesorios
        equipo.observaciones = observaciones.strip() or None

    orden = OrdenServicio(
        equipo_id=equipo.id,
        falla_reportada=falla_reportada.strip(),
        tecnico_responsable=tecnico_responsable,
        estado="Recibido",
    )
    db.add(orden)
    db.flush()

    anio = datetime.now().year
    orden.numero_orden = f"OT-{anio}-{orden.id:06d}"
    db.add(HistorialEstado(orden_id=orden.id, estado="Recibido"))
    db.commit()

    return RedirectResponse(url=f"/ordenes?ticket={orden.id}", status_code=303)


@router.post("/{orden_id}/cancelar")
def cancelar_orden(
    orden_id: int,
    motivo: str = Form(...),
    detalle: str = Form(""),
    db: Session = Depends(obtener_db),
):
    if motivo not in MOTIVOS_CANCELACION:
        raise HTTPException(status_code=400, detail="Motivo no válido")

    orden = db.get(OrdenServicio, orden_id)
    if orden is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if orden.estado == "Entregado":
        raise HTTPException(status_code=400, detail="Una orden entregada no puede cancelarse")

    cancelacion = db.query(CancelacionOrden).filter_by(orden_id=orden.id).first()
    if cancelacion is None:
        cancelacion = CancelacionOrden(
            orden_id=orden.id,
            motivo=motivo,
            detalle=detalle.strip() or None,
        )
        db.add(cancelacion)
    else:
        cancelacion.motivo = motivo
        cancelacion.detalle = detalle.strip() or None

    orden.estado = "Cancelado"
    db.add(HistorialEstado(orden_id=orden.id, estado="Cancelado"))
    db.commit()

    return RedirectResponse(url="/ordenes", status_code=303)


@router.post("/{orden_id}/eliminar")
def eliminar_orden(
    orden_id: int,
    request: Request,
    clave: str = Form(...),
    db: Session = Depends(obtener_db),
):
    if not hmac.compare_digest(clave, CLAVE_ELIMINACION):
        return templates.TemplateResponse(
            request=request,
            name="ordenes.html",
            context=contexto_ordenes(db, "La clave de eliminación es incorrecta."),
            status_code=403,
        )

    orden = db.get(OrdenServicio, orden_id)
    if orden is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    db.query(Diagnostico).filter(Diagnostico.orden_id == orden.id).delete()
    db.query(CancelacionOrden).filter(CancelacionOrden.orden_id == orden.id).delete()
    db.query(HistorialEstado).filter(HistorialEstado.orden_id == orden.id).delete()
    db.delete(orden)
    db.commit()

    return RedirectResponse(url="/ordenes", status_code=303)


@router.post("/{orden_id}/estado-rapido")
def cambiar_estado_rapido(
    orden_id: int,
    nuevo_estado: str = Form(...),
    db: Session = Depends(obtener_db),
):
    transiciones = {
        "Recibido": {"Diagnosticado"},
        "Diagnosticado": {"En reparación"},
        "En reparación": {"Listo para entrega"},
        "Listo para entrega": {"Entregado"},
    }
    orden = db.get(OrdenServicio, orden_id)
    if orden is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if nuevo_estado not in transiciones.get(orden.estado, set()):
        raise HTTPException(status_code=400, detail="Cambio de estado no permitido")

    orden.estado = nuevo_estado
    db.add(HistorialEstado(orden_id=orden.id, estado=nuevo_estado))
    db.commit()

    return RedirectResponse(url=f"/?estado={nuevo_estado}", status_code=303)


@router.get("/{orden_id}/comprobante")
def comprobante(orden_id: int, request: Request, db: Session = Depends(obtener_db)):
    orden = (
        db.query(OrdenServicio)
        .options(
            joinedload(OrdenServicio.equipo).joinedload(Equipo.cliente),
            joinedload(OrdenServicio.historial),
            joinedload(OrdenServicio.diagnostico),
        )
        .filter(OrdenServicio.id == orden_id)
        .first()
    )
    if orden is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return templates.TemplateResponse(
        request=request,
        name="comprobante.html",
        context={"orden": orden},
    )
