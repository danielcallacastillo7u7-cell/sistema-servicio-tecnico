from datetime import timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.database import obtener_db
from app.models.cliente import Cliente
from app.models.diagnostico import Diagnostico
from app.models.equipo import Equipo
from app.models.orden import OrdenServicio
from app.models.orden_equipo import OrdenEquipo
from app.models.instalacion import InstalacionCamara
from app.models.pago_internet import PagoInternet

router = APIRouter(prefix="/api", tags=["Búsqueda"])
HORA_PERU = timezone(timedelta(hours=-5))


def formatear_fecha_peru(fecha):
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(HORA_PERU).strftime("%d/%m/%Y %I:%M %p")


@router.get("/buscar")
def buscar(q: str = Query(min_length=2, max_length=100), db: Session = Depends(obtener_db)):
    # Each pasted word can match a different part of the client/equipment.
    palabras = q.split()
    if not palabras:
        return []
    patrones = ["%" + palabra.replace("/", "//").replace("%", "/%").replace("_", "/_") + "%" for palabra in palabras]
    ordenes = (
        db.query(OrdenServicio)
        .join(OrdenServicio.equipo)
        .join(Equipo.cliente)
        .outerjoin(OrdenServicio.diagnostico)
        .options(
            joinedload(OrdenServicio.recepciones), joinedload(OrdenServicio.equipo).joinedload(Equipo.cliente),
            joinedload(OrdenServicio.diagnostico),
        )
        .filter(
            and_(*(or_(
                OrdenServicio.numero_orden.ilike(patron, escape="/"),
                Cliente.nombres.ilike(patron, escape="/"),
                Cliente.apellidos.ilike(patron, escape="/"),
                Cliente.dni_ruc.ilike(patron, escape="/"),
                Cliente.telefono.ilike(patron, escape="/"),
                OrdenServicio.recepciones.any(or_(
                    OrdenEquipo.numero_serie.ilike(patron, escape="/"), OrdenEquipo.marca.ilike(patron, escape="/"),
                    OrdenEquipo.modelo.ilike(patron, escape="/"), OrdenEquipo.tipo.ilike(patron, escape="/"),
                )),
                Equipo.tipo.ilike(patron, escape="/"),
                Equipo.numero_serie.ilike(patron, escape="/"),
                Equipo.marca.ilike(patron, escape="/"),
                Equipo.modelo.ilike(patron, escape="/"),
                Diagnostico.falla_encontrada.ilike(patron, escape="/"),
                Diagnostico.solucion_recomendada.ilike(patron, escape="/"),
                Diagnostico.repuestos_necesarios.ilike(patron, escape="/"),
            ) for patron in patrones))
        )
        .order_by(OrdenServicio.id.desc())
        .limit(10)
        .all()
    )
    resultados = [
        {
            "id": orden.id,
            "numero": orden.numero_orden,
            "cliente": f"{orden.equipo.cliente.nombres} {orden.equipo.cliente.apellidos}",
            "equipo": " · ".join(f"{e.tipo} {e.marca} {e.modelo or ''}" for e in orden.equipos_recibidos),
            "equipos": [dict(tipo=e.tipo, marca=e.marca, modelo=e.modelo, serie=e.numero_serie or "Sin serie", accesorios=e.accesorios or "Ninguno", observaciones=e.observaciones or "Sin observaciones") for e in orden.equipos_recibidos],
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
                    "imagenes": [
                        {
                            "url": f"/diagnosticos/imagenes/{imagen.id}",
                            "nombre": imagen.nombre_archivo,
                        }
                        for imagen in orden.diagnostico.imagenes
                    ],
                }
                if orden.diagnostico
                else None
            ),
        }
        for orden in ordenes
    ]
    for modelo, tipo in ((InstalacionCamara, 'instalacion'), (PagoInternet, 'pago')):
        campos = ['direccion', 'nombres', 'apellidos', 'dni_ruc'] if tipo == 'instalacion' else ['direccion', 'titular', 'dni', 'periodo']
        registros = db.query(modelo).filter(and_(*(or_(*(modelo.datos[campo].as_string().ilike(patron, escape='/') for campo in campos)) for patron in patrones))).order_by(modelo.id.desc()).limit(10).all()
        for registro in registros:
            d = registro.datos
            resultados.append({
                'id': f'{tipo}-{registro.id}',
                'numero': registro.numero,
                'cliente': f"{d.get('nombres', '')} {d.get('apellidos', '')}" if tipo == 'instalacion' else d.get('titular', ''),
                'equipo': d.get('direccion', ''),
                'estado': 'Instalación' if tipo == 'instalacion' else 'Pago de internet',
                'reporte_url': f'/camaras/{registro.id}/reporte' if tipo == 'instalacion' else f'/pagos-internet/{registro.id}/ticket',
            })
    return resultados



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
