from fastapi import HTTPException
from app.models.bloqueo_cliente import BloqueoCliente
def bloqueo_activo(db,documento):
    return db.query(BloqueoCliente).filter_by(documento=documento.strip(),activo=True).first()
def comprobar_atencion(db,documento):
    if bloqueo_activo(db,documento):
        raise HTTPException(403,'Atención bloqueada por morosidad para este DNI/RUC. Solicita al encargado el desbloqueo en Inicio → Morosidad.')
