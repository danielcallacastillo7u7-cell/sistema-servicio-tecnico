from datetime import datetime, timedelta, timezone
from pathlib import Path
import hmac
import hashlib
from uuid import UUID
from app.models.solicitud_equipo import SolicitudEquipo
import json
from sqlalchemy.exc import IntegrityError
from app.models.orden_equipo import OrdenEquipo
import os
import re

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse, Response
from urllib.parse import urlencode
from app.services.ticket_pdf import generar_ticket_pdf
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import obtener_db
from app.models.cancelacion import CancelacionOrden
from app.models.cliente import Cliente
from app.services.clientes import datos_cliente_coinciden
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
ZONA_HORARIA_PERU = timezone(timedelta(hours=-5), name="America/Lima")


def fecha_hora_peru(fecha: datetime) -> datetime:
    """Convierte fechas de la base de datos (UTC) a la hora oficial de Perú."""
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(ZONA_HORARIA_PERU)


templates.env.filters["fecha_peru"] = fecha_hora_peru


def contexto_ordenes(
    db: Session,
    error: str | None = None,
    ticket_id: int | None = None,
):
    ordenes = (
        db.query(OrdenServicio)
        .options(joinedload(OrdenServicio.recepciones), joinedload(OrdenServicio.equipo).joinedload(Equipo.cliente))
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
            .options(joinedload(OrdenServicio.recepciones), joinedload(OrdenServicio.equipo).joinedload(Equipo.cliente))
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


CAMPOS_EQUIPO = {
    "tipo": 80, "tipo_otro": 80, "marca": 80, "modelo": 100,
    "numero_serie": 100, "accesorio_opcion": 20,
    "accesorios_detalle": 500, "observaciones": 1000,
}


def validar_equipos(datos):
    if not isinstance(datos, list) or not datos:
        raise ValueError("Agrega al menos un equipo.")
    resultado, series = [], set()
    for posicion, dato in enumerate(datos, 1):
        if not isinstance(dato, dict):
            raise ValueError(f"Equipo {posicion}: formato incorrecto.")
        limpio = {}
        for campo, limite in CAMPOS_EQUIPO.items():
            valor = dato.get(campo, "")
            if not isinstance(valor, str) or len(valor) > limite:
                raise ValueError(f"Equipo {posicion}: revisa el campo {campo} (máximo {limite} caracteres).")
            limpio[campo] = valor.strip()
        tipo = limpio["tipo"]
        if tipo not in {"Laptop", "Impresora", "CPU", "Otro"}:
            raise ValueError(f"Equipo {posicion}: selecciona un tipo válido.")
        if tipo == "Otro" and not limpio["tipo_otro"]:
            raise ValueError(f"Equipo {posicion}: especifica el tipo.")
        if not limpio["modelo"]:
            raise ValueError(f"Equipo {posicion}: el modelo es obligatorio.")
        opcion = limpio["accesorio_opcion"]
        if opcion == "Ninguno":
            accesorios = "Ninguno"
        elif opcion == "Especificar" and limpio["accesorios_detalle"]:
            accesorios = limpio["accesorios_detalle"]
        else:
            raise ValueError(f"Equipo {posicion}: indica los accesorios o selecciona Ninguno.")
        serie = limpio["numero_serie"] or None
        if serie and serie in series:
            raise ValueError(f"Equipo {posicion}: el número de serie está repetido en esta orden.")
        if serie:
            series.add(serie)
        resultado.append(dict(
            tipo=limpio["tipo_otro"] if tipo == "Otro" else tipo,
            marca=limpio["marca"] or "Sin especificar", modelo=limpio["modelo"],
            numero_serie=serie, accesorios=accesorios,
            observaciones=limpio["observaciones"] or None,
        ))
    return resultado


def respuesta_equipo(orden):
    return JSONResponse({
        "id": orden.id, "numero_orden": orden.numero_orden, "estado": orden.estado,
        "ticket_url": f"/ordenes/{orden.id}/ticket",
    })


@router.post("/guardar-equipo")
@router.post("")
async def registrar_orden(request: Request, db: Session = Depends(obtener_db)):
    formulario = await request.form()
    valores = {k: v for k, v in formulario.items() if isinstance(v, str)}

    individual = request.url.path.endswith("/guardar-equipo")

    def error(mensaje, estado=400):
        db.rollback()
        if individual:
            return JSONResponse({"detail": mensaje}, status_code=estado)
        contexto = contexto_ordenes(db, mensaje)
        contexto["formulario_previo"] = valores
        return templates.TemplateResponse(request=request, name="ordenes.html", context=contexto, status_code=estado)

    token, huella = None, None
    if individual:
        try:
            token = str(UUID(valores.get("solicitud_token", "")))
        except ValueError:
            return error("No se pudo identificar el guardado. Vuelve a abrir el formulario.")
        contenido = {k: v for k, v in valores.items() if k != "solicitud_token"}
        huella = hashlib.sha256(json.dumps(contenido, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        previa = db.get(SolicitudEquipo, token)
        if previa:
            if previa.huella != huella:
                return error("Este guardado ya se registró con otros datos. Revisa su ticket.", 409)
            return respuesta_equipo(db.get(OrdenServicio, previa.orden_id))

    nombres = " ".join(valores.get("nombres", "").split())
    apellidos = " ".join(valores.get("apellidos", "").split())
    dni_ruc = valores.get("dni_ruc", "").strip()
    telefono = valores.get("telefono", "").strip()
    falla = valores.get("falla_reportada", "").strip()
    tecnico = valores.get("tecnico_responsable", "")
    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,100}", nombres):
        return error("Los nombres solo pueden contener letras y espacios.")
    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,100}", apellidos):
        return error("Los apellidos solo pueden contener letras y espacios.")
    if not re.fullmatch(r"(?:[0-9]{8}|[0-9]{11})", dni_ruc):
        return error("El DNI debe tener 8 dígitos o el RUC 11 dígitos.")
    if not re.fullmatch(r"9[0-9]{8}", telefono):
        return error("El celular peruano debe comenzar con 9 y tener 9 dígitos.")
    if not falla:
        return error("La falla indicada por el cliente es obligatoria.")
    if not db.query(Trabajador).filter(Trabajador.nombre == tecnico, Trabajador.activo.is_(True)).first():
        return error("Selecciona un técnico responsable registrado.")
    try:
        # Los envíos anteriores sin JSON siguen creando una orden de un equipo.
        datos = json.loads(valores["equipos_json"]) if valores.get("equipos_json") else [valores]
    except (ValueError, TypeError):
        return error("No se pudo leer la lista de equipos.")
    try:
        equipos = validar_equipos(datos)
        if individual and len(equipos) != 1:
            raise ValueError("Guarda un solo equipo con cada botón.")
    except ValueError as exc:
        return error(str(exc))

    try:
        cliente = db.query(Cliente).filter(Cliente.dni_ruc == dni_ruc).first()
        if cliente is None:
            cliente = Cliente(nombres=nombres, apellidos=apellidos, dni_ruc=dni_ruc, telefono=telefono)
            db.add(cliente)
            db.flush()
        elif not datos_cliente_coinciden(cliente, nombres, apellidos, telefono):
            return error("Este DNI/RUC ya pertenece a un cliente registrado. Usa sus datos guardados; una nueva orden no puede modificarlos.", 409)

        recibidos = []
        for posicion, datos_equipo in enumerate(equipos, 1):
            serie = datos_equipo["numero_serie"]
            equipo = db.query(Equipo).filter(Equipo.numero_serie == serie).first() if serie else None
            if equipo is not None and equipo.cliente_id != cliente.id:
                return error(f"Equipo {posicion}: ese número de serie pertenece a otro cliente.", 409)
            if equipo is None:
                equipo = Equipo(cliente_id=cliente.id, **datos_equipo)
                db.add(equipo)
                db.flush()
            else:
                for campo, valor in datos_equipo.items():
                    setattr(equipo, campo, valor)
            recibidos.append(OrdenEquipo(equipo_id=equipo.id, posicion=posicion, **datos_equipo))

        orden = OrdenServicio(
            equipo_id=recibidos[0].equipo_id, recepciones=recibidos,
            falla_reportada=falla, tecnico_responsable=tecnico, estado="Recibido",
        )
        db.add(orden)
        db.flush()
        anio = datetime.now(ZONA_HORARIA_PERU).year
        orden.numero_orden = f"OT-{anio}-{orden.id:06d}"
        db.add(HistorialEstado(orden_id=orden.id, estado="Recibido"))
        if individual:
            db.add(SolicitudEquipo(token=token, huella=huella, orden_id=orden.id))
        db.commit()
    except IntegrityError:
        db.rollback()
        previa = db.get(SolicitudEquipo, token) if individual else None
        if previa and previa.huella == huella:
            return respuesta_equipo(db.get(OrdenServicio, previa.orden_id))
        return error("No se pudo guardar: un cliente o número de serie se registró simultáneamente. Revisa los datos y vuelve a intentar.", 409)
    except Exception:
        db.rollback()
        raise
    if individual:
        return respuesta_equipo(orden)
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
            joinedload(OrdenServicio.recepciones), joinedload(OrdenServicio.equipo).joinedload(Equipo.cliente),
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


@router.get("/{orden_id}/ticket")
def ticket_individual(orden_id: int, request: Request, db: Session = Depends(obtener_db)):
    orden = db.query(OrdenServicio).options(
        joinedload(OrdenServicio.recepciones),
        joinedload(OrdenServicio.equipo).joinedload(Equipo.cliente),
    ).filter(OrdenServicio.id == orden_id).first()
    if orden is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return templates.TemplateResponse(request=request, name="ticket_inline.html", context={"ticket_orden": orden})


@router.get("/{orden_id}/ticket.pdf")
def descargar_ticket(orden_id: int, request: Request, db: Session = Depends(obtener_db)):
    orden = db.query(OrdenServicio).options(
        joinedload(OrdenServicio.recepciones),
        joinedload(OrdenServicio.equipo).joinedload(Equipo.cliente),
    ).filter(OrdenServicio.id == orden_id).first()
    if orden is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    html = templates.get_template("ticket_contenido.html").render(request=request, ticket_orden=orden)
    numero = re.sub(r"[^A-Za-z0-9_-]", "_", orden.numero_orden or str(orden.id))
    return Response(generar_ticket_pdf(html, numero), media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="Ticket-{numero}.pdf"',
        "Cache-Control": "no-store",
    })


@router.get("/{orden_id}/ticket/whatsapp")
def whatsapp_ticket(orden_id: int, db: Session = Depends(obtener_db)):
    orden = db.get(OrdenServicio, orden_id)
    if orden is None:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    telefono = re.sub(r"\D", "", orden.equipo.cliente.telefono or "")
    if re.fullmatch(r"9[0-9]{8}", telefono):
        telefono = "51" + telefono
    if not re.fullmatch(r"519[0-9]{8}", telefono):
        raise HTTPException(status_code=400, detail="Revisa el celular peruano del cliente antes de abrir WhatsApp.")
    mensaje = f"Hola, le compartimos el ticket de recepción {orden.numero_orden} de ServiTech. Gracias por su confianza."
    return RedirectResponse("https://wa.me/" + telefono + "?" + urlencode({"text": mensaje}), status_code=303)
