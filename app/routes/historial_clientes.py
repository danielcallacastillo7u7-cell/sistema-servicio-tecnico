from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import obtener_db
from app.models.cliente import Cliente
from app.models.equipo import Equipo
from app.models.orden import OrdenServicio
from app.models.orden_equipo import OrdenEquipo
from app.models.diagnostico import Diagnostico
from app.routes.busqueda import formatear_fecha_peru

router = APIRouter(prefix="/api", tags=["Historial de clientes"])


def datos_cliente(c):
    return dict(id=c.id, nombres=c.nombres, apellidos=c.apellidos, dni_ruc=c.dni_ruc, telefono=c.telefono)


def datos_equipo(e):
    return dict(id=e.equipo_id if isinstance(e, OrdenEquipo) else e.id, tipo=e.tipo, marca=e.marca,
                modelo=e.modelo or "", serie=e.numero_serie or "Sin serie", accesorios=e.accesorios or "Ninguno",
                observaciones=e.observaciones or "Sin observaciones")


def patron_busqueda(q):
    return '%' + q.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'


@router.get("")
def buscar_clientes(q: str = Query(default="", max_length=100), pagina: int = Query(default=1, ge=1), db: Session = Depends(obtener_db)):
    consulta = db.query(Cliente)
    if q.strip():
        patron = patron_busqueda(q)
        consulta = consulta.filter(or_(
            (Cliente.nombres + ' ' + Cliente.apellidos).ilike(patron, escape='\\'),
            Cliente.dni_ruc.ilike(patron, escape='\\'), Cliente.telefono.ilike(patron, escape='\\'),
        ))
    total = consulta.count()
    paginas = max(1, (total + 19) // 20)
    pagina = min(pagina, paginas)
    clientes = consulta.order_by(Cliente.nombres, Cliente.apellidos, Cliente.id).offset((pagina-1)*20).limit(20).all()
    resumenes = {}
    if clientes:
        resumen = db.query(
            Equipo.cliente_id.label('cliente_id'), OrdenServicio.numero_orden, OrdenServicio.fecha_ingreso,
            OrdenServicio.estado,
            func.count(OrdenServicio.id).over(partition_by=Equipo.cliente_id).label('cantidad'),
            func.row_number().over(partition_by=Equipo.cliente_id,
                order_by=(OrdenServicio.fecha_ingreso.desc(), OrdenServicio.id.desc())).label('posicion'),
        ).join(OrdenServicio.equipo).filter(Equipo.cliente_id.in_([c.id for c in clientes])).subquery()
        resumenes = {r.cliente_id: r for r in db.query(resumen).filter(resumen.c.posicion == 1).all()}
    filas = []
    for c in clientes:
        r = resumenes.get(c.id)
        filas.append({**datos_cliente(c), 'total_reparaciones': r.cantidad if r else 0,
            'ultima_reparacion': None if r is None else dict(numero=r.numero_orden,
                fecha=formatear_fecha_peru(r.fecha_ingreso), estado=r.estado)})
    return dict(clientes=filas, total=total, pagina=pagina, paginas=paginas)


@router.get("/{cliente_id}/historial")
def historial_cliente(cliente_id: int, q: str = Query(default="", max_length=100),
                      pagina: int = Query(default=1, ge=1), equipo_id: int | None = Query(default=None, ge=1),
                      db: Session = Depends(obtener_db)):
    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise HTTPException(404, "Cliente no encontrado")
    equipos = db.query(Equipo).filter(Equipo.cliente_id == cliente_id).order_by(Equipo.id.desc()).all()
    if equipo_id is not None and not any(e.id == equipo_id for e in equipos):
        raise HTTPException(404, "El equipo no pertenece a este cliente")
    consulta = db.query(OrdenServicio).filter(OrdenServicio.equipo.has(Equipo.cliente_id == cliente_id))
    total_ordenes = consulta.count()
    if equipo_id is not None:
        consulta = consulta.filter(or_(
            OrdenServicio.recepciones.any(OrdenEquipo.equipo_id == equipo_id),
            ~OrdenServicio.recepciones.any() & (OrdenServicio.equipo_id == equipo_id),
        ))
    if q.strip():
        patron = patron_busqueda(q)
        consulta = consulta.filter(or_(
            OrdenServicio.numero_orden.ilike(patron, escape='\\'),
            OrdenServicio.falla_reportada.ilike(patron, escape='\\'),
            OrdenServicio.estado.ilike(patron, escape='\\'),
            OrdenServicio.tecnico_responsable.ilike(patron, escape='\\'),
            OrdenServicio.recepciones.any(or_(*[
                campo.ilike(patron, escape='\\') for campo in
                (OrdenEquipo.tipo, OrdenEquipo.marca, OrdenEquipo.modelo, OrdenEquipo.numero_serie)
            ])),
            (~OrdenServicio.recepciones.any()) & OrdenServicio.equipo.has(or_(*[
                campo.ilike(patron, escape='\\') for campo in (Equipo.tipo, Equipo.marca, Equipo.modelo, Equipo.numero_serie)
            ])),
            OrdenServicio.diagnostico.has(or_(Diagnostico.falla_encontrada.ilike(patron, escape='\\'),
                                             Diagnostico.solucion_recomendada.ilike(patron, escape='\\'))),
        ))
    total = consulta.count()
    paginas = max(1, (total+9)//10)
    pagina = min(pagina, paginas)
    ordenes = consulta.options(selectinload(OrdenServicio.recepciones), joinedload(OrdenServicio.equipo),
        joinedload(OrdenServicio.diagnostico).selectinload(Diagnostico.imagenes), selectinload(OrdenServicio.historial)
    ).order_by(OrdenServicio.fecha_ingreso.desc(), OrdenServicio.id.desc()).offset((pagina-1)*10).limit(10).all()
    registros = []
    for orden in ordenes:
        diag = orden.diagnostico
        registros.append(dict(
            id=orden.id, numero=orden.numero_orden, fecha=formatear_fecha_peru(orden.fecha_ingreso),
            estado=orden.estado, tecnico=orden.tecnico_responsable or 'Sin asignar', falla_reportada=orden.falla_reportada,
            equipos=[datos_equipo(e) for e in orden.equipos_recibidos],
            diagnostico=None if diag is None else dict(falla=diag.falla_encontrada, solucion=diag.solucion_recomendada,
                repuestos=diag.repuestos_necesarios or 'Ninguno', costo=f'{diag.costo_estimado:.2f}',
                imagenes=[dict(url=f'/diagnosticos/imagenes/{i.id}', nombre=i.nombre_archivo) for i in diag.imagenes]),
            historial=[dict(estado=h.estado, fecha=formatear_fecha_peru(h.fecha)) for h in orden.historial],
            ticket_url=f'/ordenes/{orden.id}/ticket',
        ))
    return dict(cliente=datos_cliente(cliente), equipos=[datos_equipo(e) for e in equipos],
                ordenes=registros, total=total, total_ordenes=total_ordenes, pagina=pagina, paginas=paginas)
