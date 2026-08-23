from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class HistorialEstado(Base):
    __tablename__ = "historial_estados"

    id = Column(Integer, primary_key=True, index=True)
    orden_id = Column(Integer, ForeignKey("ordenes_servicio.id"), nullable=False, index=True)
    estado = Column(String(50), nullable=False)
    fecha = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    orden = relationship("OrdenServicio", back_populates="historial")
