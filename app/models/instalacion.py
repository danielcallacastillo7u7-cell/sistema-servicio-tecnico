from sqlalchemy import Column, Integer, String, Date, DateTime, JSON
from datetime import datetime, timezone
from app.database import Base


class InstalacionCamara(Base):
    __tablename__ = 'instalaciones_camaras'
    id = Column(Integer, primary_key=True)
    solicitud_id = Column(String(36), unique=True, nullable=False)
    fecha_registro = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    fecha_instalacion = Column(Date, nullable=False, index=True)
    tecnico = Column(String(120), nullable=False)
    datos = Column(JSON, nullable=False)

    @property
    def numero(self):
        return f'IC-{self.id:06d}'
