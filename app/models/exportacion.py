from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class HistorialExportacion(Base):
    __tablename__ = "historial_exportaciones"

    id = Column(Integer, primary_key=True, index=True)
    tipo_informacion = Column(String(40), nullable=False, index=True)
    destino = Column(String(30), nullable=False)
    cantidad_registros = Column(Integer, nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="Completado", index=True)
    detalle = Column(Text, nullable=True)
    fecha_exportacion = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
