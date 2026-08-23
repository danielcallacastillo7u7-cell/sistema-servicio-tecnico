from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombres = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    dni_ruc = Column(String(20), unique=True, nullable=False, index=True)
    telefono = Column(String(20), nullable=False, index=True)
    fecha_registro = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    equipos = relationship("Equipo", back_populates="cliente")
