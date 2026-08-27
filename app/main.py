from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.gzip import GZipMiddleware
from sqlalchemy import func, text
from sqlalchemy.orm import Session, joinedload

from app.database import Base, engine, obtener_db
from app.models.cliente import Cliente
from app.models.cancelacion import CancelacionOrden
from app.models.diagnostico import Diagnostico
from app.models.equipo import Equipo
from app.models.historial import HistorialEstado
from app.models.orden import OrdenServicio
from app.models.trabajador import Trabajador
from app.routes.clientes import router as clientes_router
from app.routes.busqueda import router as busqueda_router
from app.routes.ajustes import router as ajustes_router
from app.routes.diagnosticos import router as diagnosticos_router
from app.routes.equipos import router as equipos_router
from app.routes.ordenes import router as ordenes_router

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="ServiTech")
app.add_middleware(GZipMiddleware, minimum_size=500)

# Crea en PostgreSQL local las tablas de los modelos importados.
Base.metadata.create_all(bind=engine)

app.include_router(clientes_router)
app.include_router(ajustes_router)
app.include_router(busqueda_router)
app.include_router(diagnosticos_router)
app.include_router(equipos_router)
app.include_router(ordenes_router)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/")
def inicio(
    request: Request,
    estado: str | None = Query(default=None),
    db: Session = Depends(obtener_db),
):
    conteos = dict(
        db.query(OrdenServicio.estado, func.count(OrdenServicio.id))
        .filter(
            OrdenServicio.estado.in_(
                ("Recibido", "Diagnosticado", "En reparación", "Listo para entrega")
            )
        )
        .group_by(OrdenServicio.estado)
        .all()
    )
    estados = {
        "recibidos": conteos.get("Recibido", 0),
        "diagnosticados": conteos.get("Diagnosticado", 0),
        "reparacion": conteos.get("En reparación", 0),
        "listos": conteos.get("Listo para entrega", 0),
    }
    total_ordenes = db.query(func.count(OrdenServicio.id)).scalar() or 0
    total_canceladas = (
        db.query(func.count(OrdenServicio.id))
        .filter(OrdenServicio.estado == "Cancelado")
        .scalar()
        or 0
    )
    ultimas_ordenes = (
        db.query(OrdenServicio)
        .options(
            joinedload(OrdenServicio.equipo).joinedload(Equipo.cliente),
            joinedload(OrdenServicio.diagnostico),
        )
        .order_by(OrdenServicio.id.desc())
        .limit(5)
        .all()
    )
    estados_panel_validos = {
        "Todas",
        "Recibido",
        "Diagnosticado",
        "En reparación",
        "Listo para entrega",
        "Cancelado",
    }
    ordenes_estado = []
    if estado in estados_panel_validos:
        consulta_ordenes = (
            db.query(OrdenServicio)
            .options(
                joinedload(OrdenServicio.equipo).joinedload(Equipo.cliente),
                joinedload(OrdenServicio.diagnostico),
            )
        )
        if estado != "Todas":
            consulta_ordenes = consulta_ordenes.filter(OrdenServicio.estado == estado)
        ordenes_estado = consulta_ordenes.order_by(OrdenServicio.id.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "titulo": "ServiTech",
            "seccion": "inicio",
            "estados": estados,
            "total_ordenes": total_ordenes,
            "total_canceladas": total_canceladas,
            "ultimas_ordenes": ultimas_ordenes,
            "estado_seleccionado": estado if estado in estados_panel_validos else None,
            "estado_titulo": (
                "Todas las órdenes" if estado == "Todas" else "Órdenes canceladas" if estado == "Cancelado" else estado
            ),
            "ordenes_estado": ordenes_estado,
        },
    )


@app.get("/api/database")
def comprobar_base_de_datos():
    with engine.connect() as conexion:
        conexion.execute(text("SELECT 1"))

    return {"database": "conectada"}
