from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Diagnostico(Base):
    __tablename__ = "diagnosticos"

    id = Column(Integer, primary_key=True, index=True)
    orden_id = Column(
        Integer,
        ForeignKey("ordenes_servicio.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )
    falla_encontrada = Column(Text, nullable=False)
    solucion_recomendada = Column(Text, nullable=False)
    repuestos_necesarios = Column(Text, nullable=True)
    costo_estimado = Column(Numeric(10, 2), nullable=False, default=0)
    fecha_diagnostico = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    orden = relationship("OrdenServicio", back_populates="diagnostico")
