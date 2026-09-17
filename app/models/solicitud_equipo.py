from sqlalchemy import Column, ForeignKey, Integer, String

from app.database import Base


class SolicitudEquipo(Base):
    """Evita repetir una orden si se reintenta un guardado sin respuesta."""
    __tablename__ = "solicitudes_equipo"

    token = Column(String(36), primary_key=True)
    huella = Column(String(64), nullable=False)
    orden_id = Column(Integer, ForeignKey("ordenes_servicio.id", ondelete="CASCADE"), nullable=False, unique=True)
