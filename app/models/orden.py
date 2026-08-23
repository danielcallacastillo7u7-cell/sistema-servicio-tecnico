from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class OrdenServicio(Base):
    __tablename__ = "ordenes_servicio"

    id = Column(Integer, primary_key=True, index=True)
    numero_orden = Column(String(30), unique=True, nullable=True, index=True)
    equipo_id = Column(
        Integer,
        ForeignKey("equipos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    falla_reportada = Column(Text, nullable=False)
    tecnico_responsable = Column(String(120), nullable=True, index=True)
    estado = Column(String(50), nullable=False, default="Recibido", index=True)
    fecha_ingreso = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    equipo = relationship("Equipo", back_populates="ordenes")
    diagnostico = relationship(
        "Diagnostico",
        back_populates="orden",
        uselist=False,
    )
    historial = relationship(
        "HistorialEstado",
        back_populates="orden",
        order_by="HistorialEstado.fecha.desc()",
    )
    cancelacion = relationship(
        "CancelacionOrden",
        back_populates="orden",
        uselist=False,
    )
