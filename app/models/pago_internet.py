from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON
from app.database import Base

class PagoInternet(Base):
    __tablename__ = 'pagos_internet'
    id = Column(Integer, primary_key=True)
    token = Column(String(36), unique=True, nullable=False)
    fecha = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    emisor = Column(String(120), nullable=False)
    datos = Column(JSON, nullable=False)
    @property
    def numero(self): return f'PI-{self.id:06d}'
