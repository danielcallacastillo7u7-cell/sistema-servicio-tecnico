from sqlalchemy import Column, Integer, String, Numeric, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Insumo(Base):
    __tablename__ = 'insumos'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(150), nullable=False)
    categoria = Column(String(80), nullable=False)
    marca = Column(String(100), nullable=False, default='')
    unidad = Column(String(40), nullable=False)
    cantidad = Column(Numeric(14, 3), nullable=False, default=0)
    stock_minimo = Column(Numeric(14, 3), nullable=False, default=0)
    precio = Column(Numeric(14, 2), nullable=True)
    descripcion = Column(Text, nullable=False, default='')
    activo = Column(Boolean, nullable=False, default=True)
    fecha = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

class MovimientoInsumo(Base):
    __tablename__ = 'movimientos_insumos'
    id = Column(Integer, primary_key=True)
    insumo_id = Column(Integer, ForeignKey('insumos.id'), nullable=False, index=True)
    cantidad = Column(Numeric(14, 3), nullable=False)
    saldo = Column(Numeric(14, 3), nullable=False)
    motivo = Column(String(250), nullable=False)
    fecha = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class OpcionInventario(Base):
    __tablename__ = 'opciones_inventario'
    id = Column(Integer, primary_key=True)
    tipo = Column(String(20), nullable=False)
    nombre = Column(String(80), nullable=False)
    clave = Column(String(120), nullable=False, unique=True)
