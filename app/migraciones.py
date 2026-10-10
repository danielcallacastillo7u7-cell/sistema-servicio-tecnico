from sqlalchemy import text


def migrar_equipos_orden(engine):
    """Backfill aditivo e idempotente; no altera ni elimina columnas anteriores."""
    with engine.begin() as conexion:
        conexion.execute(text("""
            INSERT INTO orden_equipos
                (orden_id, equipo_id, posicion, tipo, marca, modelo,
                 numero_serie, accesorios, observaciones)
            SELECT o.id, e.id, 1, e.tipo, e.marca, e.modelo,
                   e.numero_serie, e.accesorios, e.observaciones
            FROM ordenes_servicio o JOIN equipos e ON e.id = o.equipo_id
            WHERE NOT EXISTS (
                SELECT 1 FROM orden_equipos oe WHERE oe.orden_id = o.id
            )
            ON CONFLICT DO NOTHING
        """))


def migrar_detalles_servicio(engine):
    from sqlalchemy import inspect
    columnas = {c['name'] for c in inspect(engine).get_columns('ordenes_servicio')}
    with engine.begin() as conexion:
        for nombre, tipo in [('otro_producto_servicio','TEXT'), ('servicio_domicilio','BOOLEAN'), ('motivo_no_reparado','TEXT'), ('fecha_no_reparado','TIMESTAMP')]:
            if nombre not in columnas:
                conexion.execute(text(f'ALTER TABLE ordenes_servicio ADD COLUMN {nombre} {tipo}'))
