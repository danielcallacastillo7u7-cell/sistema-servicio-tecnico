from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Equipo(Base):
    __tablename__ = "equipos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(
        Integer,
        ForeignKey("clientes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tipo = Column(String(80), nullable=False, index=True)
    marca = Column(String(80), nullable=False)
    modelo = Column(String(100), nullable=True)
    numero_serie = Column(String(100), nullable=True, unique=True, index=True)
    accesorios = Column(Text, nullable=True)
    observaciones = Column(Text, nullable=True)
    fecha_registro = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    cliente = relationship("Cliente", back_populates="equipos")
    ordenes = relationship("OrdenServicio", back_populates="equipo")
