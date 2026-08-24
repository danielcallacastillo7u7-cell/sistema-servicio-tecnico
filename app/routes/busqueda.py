from datetime import timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database import obtener_db
from app.models.cliente import Cliente
from app.models.diagnostico import Diagnostico
from app.models.equipo import Equipo
from app.models.orden import OrdenServicio

router = APIRouter(prefix="/api", tags=["Búsqueda"])
HORA_PERU = timezone(timedelta(hours=-5))


def formatear_fecha_peru(fecha):
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(HORA_PERU).strftime("%d/%m/%Y %I:%M %p")


@router.get("/buscar")
def buscar(q: str = Query(min_length=2, max_length=100), db: Session = Depends(obtener_db)):
    patron = f"%{q.strip()}%"
    ordenes = (
        db.query(OrdenServicio)
        .join(OrdenServicio.equipo)
        .join(Equipo.cliente)
        .outerjoin(OrdenServicio.diagnostico)
        .options(
            joinedload(OrdenServicio.equipo).joinedload(Equipo.cliente),
            joinedload(OrdenServicio.diagnostico),
        )
        .filter(
            or_(
                OrdenServicio.numero_orden.ilike(patron),
                Cliente.nombres.ilike(patron),
                Cliente.apellidos.ilike(patron),
                Cliente.dni_ruc.ilike(patron),
                Cliente.telefono.ilike(patron),
                Equipo.numero_serie.ilike(patron),
                Equipo.marca.ilike(patron),
                Equipo.modelo.ilike(patron),
                Diagnostico.falla_encontrada.ilike(patron),
                Diagnostico.solucion_recomendada.ilike(patron),
                Diagnostico.repuestos_necesarios.ilike(patron),
            )
        )
        .order_by(OrdenServicio.id.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "id": orden.id,
            "numero": orden.numero_orden,
            "cliente": f"{orden.equipo.cliente.nombres} {orden.equipo.cliente.apellidos}",
            "equipo": f"{orden.equipo.tipo} {orden.equipo.marca}",
            "estado": orden.estado,
            "fecha": formatear_fecha_peru(orden.fecha_ingreso),
            "datos_cliente": {
                "nombres": f"{orden.equipo.cliente.nombres} {orden.equipo.cliente.apellidos}",
                "documento": orden.equipo.cliente.dni_ruc,
                "telefono": orden.equipo.cliente.telefono,
            },
            "datos_equipo": {
                "tipo": orden.equipo.tipo,
                "marca": orden.equipo.marca or "No indicada",
                "modelo": orden.equipo.modelo or "No indicado",
                "serie": orden.equipo.numero_serie or "Sin serie",
                "accesorios": orden.equipo.accesorios or "Ninguno",
                "observaciones": orden.equipo.observaciones or "Sin observaciones",
            },
            "datos_orden": {
                "falla_reportada": orden.falla_reportada,
                "tecnico": orden.tecnico_responsable or "Sin asignar",
            },
            "especificaciones": (
                {
                    "falla_encontrada": orden.diagnostico.falla_encontrada,
                    "solucion": orden.diagnostico.solucion_recomendada,
                    "repuestos": orden.diagnostico.repuestos_necesarios or "Ninguno",
                    "costo": f"{orden.diagnostico.costo_estimado:.2f}",
                }
                if orden.diagnostico
                else None
            ),
        }
        for orden in ordenes
    ]


@router.get("/alertas")
def alertas(db: Session = Depends(obtener_db)):
    pendientes = (
        db.query(OrdenServicio)
        .filter(
            OrdenServicio.estado == "Recibido",
            OrdenServicio.diagnostico == None,  # noqa: E711
        )
        .count()
    )
    return {"diagnosticos_pendientes": pendientes}
