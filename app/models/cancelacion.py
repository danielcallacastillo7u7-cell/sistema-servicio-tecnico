from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CancelacionOrden(Base):
    __tablename__ = "cancelaciones_orden"

    id = Column(Integer, primary_key=True, index=True)
    orden_id = Column(Integer, ForeignKey("ordenes_servicio.id"), unique=True, nullable=False)
    motivo = Column(String(100), nullable=False)
    detalle = Column(Text, nullable=True)
    fecha = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    orden = relationship("OrdenServicio", back_populates="cancelacion")
