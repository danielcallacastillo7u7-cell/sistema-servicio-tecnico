from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Trabajador(Base):
    __tablename__ = "trabajadores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), unique=True, nullable=False, index=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
