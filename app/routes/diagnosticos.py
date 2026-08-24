from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import obtener_db
from app.models.diagnostico import Diagnostico, DiagnosticoImagen
from app.models.equipo import Equipo
from app.models.orden import OrdenServicio

router = APIRouter(prefix="/diagnosticos", tags=["Diagnósticos"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)
TIPOS_IMAGEN_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
MAXIMO_IMAGENES = 5
MAXIMO_BYTES_IMAGEN = 4 * 1024 * 1024


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
        falla_encontrada=falla_encontrada.strip(),
        solucion_recomendada=solucion_recomendada.strip(),
        repuestos_necesarios=repuestos_necesarios.strip() or None,
        costo_estimado=costo,
    )
    orden.estado = "Diagnosticado"
    db.add(diagnostico)
    db.flush()
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
