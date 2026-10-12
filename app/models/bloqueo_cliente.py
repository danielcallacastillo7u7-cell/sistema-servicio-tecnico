from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base
class BloqueoCliente(Base):
    __tablename__='bloqueos_clientes'
    id=Column(Integer,primary_key=True)
    documento=Column(String(11),nullable=False,index=True)
    nombre=Column(String(200),nullable=False)
    motivo=Column(String(1000),nullable=False)
    monto=Column(Numeric(12,2),nullable=True)
    activo=Column(Boolean,nullable=False,default=True)
    fecha=Column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    desbloqueado=Column(DateTime(timezone=True),nullable=True)
