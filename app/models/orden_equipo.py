from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class OrdenEquipo(Base):
    """Equipo recibido y copia de sus datos en el momento de la recepción."""
    __tablename__ = "orden_equipos"
    __table_args__ = (
        UniqueConstraint("orden_id", "equipo_id"),
        UniqueConstraint("orden_id", "posicion"),
    )

    id = Column(Integer, primary_key=True)
    orden_id = Column(Integer, ForeignKey("ordenes_servicio.id", ondelete="CASCADE"), nullable=False, index=True)
    equipo_id = Column(Integer, ForeignKey("equipos.id", ondelete="RESTRICT"), nullable=False, index=True)
    posicion = Column(Integer, nullable=False)
    tipo = Column(String(80), nullable=False)
    marca = Column(String(80), nullable=False)
    modelo = Column(String(100))
    numero_serie = Column(String(100))
    accesorios = Column(Text)
    observaciones = Column(Text)

    orden = relationship("OrdenServicio", back_populates="recepciones")
    equipo = relationship("Equipo")
