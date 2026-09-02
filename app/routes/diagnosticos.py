from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import obtener_db
from app.models.diagnostico import Diagnostico, DiagnosticoImagen, DiagnosticoMensaje
from app.models.equipo import Equipo
from app.models.orden import OrdenServicio

router = APIRouter(prefix="/diagnosticos", tags=["Diagnósticos"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)
TIPOS_IMAGEN_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
MAXIMO_IMAGENES = 5
MAXIMO_BYTES_IMAGEN = 4 * 1024 * 1024


class DiagnosticoActualizacion(BaseModel):
    falla_encontrada: str
    solucion_recomendada: str
    repuestos_necesarios: str = ""
    costo_estimado: str


def validar_datos_diagnostico(
    falla_encontrada: str,
    solucion_recomendada: str,
    repuestos_necesarios: str,
    costo_estimado: str,
):
    falla = falla_encontrada.strip()
    solucion = solucion_recomendada.strip()
    if not falla or not solucion:
        raise ValueError("La falla encontrada y la solución recomendada son obligatorias.")
    try:
        costo = Decimal(costo_estimado.strip() or "0")
        if not costo.is_finite() or costo < 0 or costo > Decimal("99999999.99"):
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        raise ValueError("Ingresa un costo válido entre S/ 0.00 y S/ 99,999,999.99.") from None
    return falla, solucion, repuestos_necesarios.strip() or None, costo


def crear_mensaje_cliente(diagnostico: Diagnostico) -> str:
    orden = diagnostico.orden
    equipo = orden.equipo
    cliente = equipo.cliente
    repuestos = diagnostico.repuestos_necesarios or "No se requieren repuestos por el momento"
    descripcion_equipo = " ".join(filter(None, (equipo.tipo, equipo.marca, equipo.modelo)))
    return (
        f"Hola {cliente.nombres}, le informamos que el diagnóstico de su equipo "
        f"{descripcion_equipo}, correspondiente a la orden {orden.numero_orden}, está listo.\n\n"
        f"Falla encontrada: {diagnostico.falla_encontrada}\n"
        f"Solución recomendada: {diagnostico.solucion_recomendada}\n"
        f"Repuestos necesarios: {repuestos}\n"
        f"Costo estimado: S/ {diagnostico.costo_estimado:.2f}\n\n"
        "Por favor, responda este mensaje para confirmar si autoriza el servicio.\n\n"
        "ServiTech"
    )


def numero_whatsapp(telefono: str) -> str:
    numero = "".join(caracter for caracter in telefono if caracter.isdigit())
    return f"51{numero}" if len(numero) == 9 else numero


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
            .joinedload(Equipo.cliente),
            joinedload(Diagnostico.mensaje_cliente),
        )
        .order_by(Diagnostico.id.desc())
        .all()
    )
    mensajes = {}
    for diagnostico in diagnosticos:
        if diagnostico.mensaje_cliente:
            telefono = diagnostico.orden.equipo.cliente.telefono
            mensajes[diagnostico.id] = {
                "registro": diagnostico.mensaje_cliente,
                "url_whatsapp": f"https://wa.me/{numero_whatsapp(telefono)}?text={quote(diagnostico.mensaje_cliente.mensaje)}",
            }
    return {
        "ordenes_pendientes": ordenes_pendientes,
        "diagnosticos": diagnosticos,
        "mensajes": mensajes,
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
    imagenes: list[UploadFile] = File(default=[]),
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
        falla, solucion, repuestos, costo = validar_datos_diagnostico(
            falla_encontrada, solucion_recomendada, repuestos_necesarios, costo_estimado
        )
    except ValueError as error:
        return templates.TemplateResponse(
            request=request,
            name="diagnosticos.html",
            context=contexto_diagnosticos(db, str(error)),
            status_code=400,
        )

    archivos = [archivo for archivo in imagenes if archivo.filename]
    if len(archivos) > MAXIMO_IMAGENES:
        return templates.TemplateResponse(
            request=request,
            name="diagnosticos.html",
            context=contexto_diagnosticos(db, "Puedes adjuntar como máximo 5 imágenes."),
            status_code=400,
        )

    evidencias = []
    for archivo in archivos:
        if archivo.content_type not in TIPOS_IMAGEN_PERMITIDOS:
            return templates.TemplateResponse(
                request=request,
                name="diagnosticos.html",
                context=contexto_diagnosticos(db, "Las evidencias deben ser imágenes JPG, PNG o WebP."),
                status_code=400,
            )
        contenido = archivo.file.read(MAXIMO_BYTES_IMAGEN + 1)
        if len(contenido) > MAXIMO_BYTES_IMAGEN:
            return templates.TemplateResponse(
                request=request,
                name="diagnosticos.html",
                context=contexto_diagnosticos(db, "Cada imagen puede pesar como máximo 4 MB."),
                status_code=400,
            )
        evidencias.append((archivo, contenido))

    diagnostico = Diagnostico(
        orden_id=orden_id,
        falla_encontrada=falla,
        solucion_recomendada=solucion,
        repuestos_necesarios=repuestos,
        costo_estimado=costo,
    )
    orden.estado = "Diagnosticado"
    db.add(diagnostico)
    try:
        db.flush()
        db.add(DiagnosticoMensaje(diagnostico_id=diagnostico.id, mensaje=crear_mensaje_cliente(diagnostico), estado="Pendiente"))
        for archivo, contenido in evidencias:
            db.add(
                DiagnosticoImagen(
                    diagnostico_id=diagnostico.id,
                    nombre_archivo=Path(archivo.filename).name[:255],
                    tipo_contenido=archivo.content_type,
                    contenido=contenido,
                )
            )
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request=request,
            name="diagnosticos.html",
            context=contexto_diagnosticos(db, "La orden seleccionada ya tiene un diagnóstico."),
            status_code=409,
        )

    return RedirectResponse(url="/diagnosticos", status_code=303)


@router.get("/api/{diagnostico_id}")
def obtener_diagnostico(diagnostico_id: int, db: Session = Depends(obtener_db)):
    diagnostico = db.get(Diagnostico, diagnostico_id)
    if diagnostico is None:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    return {
        "id": diagnostico.id,
        "orden_id": diagnostico.orden_id,
        "numero_orden": diagnostico.orden.numero_orden,
        "falla_encontrada": diagnostico.falla_encontrada,
        "solucion_recomendada": diagnostico.solucion_recomendada,
        "repuestos_necesarios": diagnostico.repuestos_necesarios or "",
        "costo_estimado": str(diagnostico.costo_estimado),
    }


@router.put("/api/{diagnostico_id}")
def actualizar_diagnostico(
    diagnostico_id: int,
    datos: DiagnosticoActualizacion,
    db: Session = Depends(obtener_db),
):
    diagnostico = db.get(Diagnostico, diagnostico_id)
    if diagnostico is None:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    try:
        falla, solucion, repuestos, costo = validar_datos_diagnostico(
            datos.falla_encontrada,
            datos.solucion_recomendada,
            datos.repuestos_necesarios,
            datos.costo_estimado,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    diagnostico.falla_encontrada = falla
    diagnostico.solucion_recomendada = solucion
    diagnostico.repuestos_necesarios = repuestos
    diagnostico.costo_estimado = costo
    if diagnostico.mensaje_cliente and diagnostico.mensaje_cliente.estado == "Pendiente":
        diagnostico.mensaje_cliente.mensaje = crear_mensaje_cliente(diagnostico)
    db.commit()
    db.refresh(diagnostico)
    return {"mensaje": "Diagnóstico actualizado correctamente", "id": diagnostico.id}


@router.post("/{diagnostico_id}/mensaje/preparar")
def preparar_mensaje(diagnostico_id: int, db: Session = Depends(obtener_db)):
    diagnostico = db.get(Diagnostico, diagnostico_id)
    if diagnostico is None:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    if diagnostico.mensaje_cliente is None:
        db.add(DiagnosticoMensaje(diagnostico_id=diagnostico.id, mensaje=crear_mensaje_cliente(diagnostico), estado="Pendiente"))
        db.commit()
    return RedirectResponse(url="/diagnosticos", status_code=303)


@router.post("/{diagnostico_id}/mensaje/estado")
def cambiar_estado_mensaje(
    diagnostico_id: int,
    estado: str = Form(...),
    db: Session = Depends(obtener_db),
):
    if estado not in {"Pendiente", "Enviado", "No enviar"}:
        raise HTTPException(status_code=422, detail="Estado de mensaje no válido")
    mensaje = db.query(DiagnosticoMensaje).filter(DiagnosticoMensaje.diagnostico_id == diagnostico_id).first()
    if mensaje is None:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    mensaje.estado = estado
    db.commit()
    return RedirectResponse(url="/diagnosticos", status_code=303)


@router.get("/imagenes/{imagen_id}")
def ver_imagen_diagnostico(imagen_id: int, db: Session = Depends(obtener_db)):
    imagen = db.get(DiagnosticoImagen, imagen_id)
    if imagen is None:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return Response(
        content=imagen.contenido,
        media_type=imagen.tipo_contenido,
        headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )
