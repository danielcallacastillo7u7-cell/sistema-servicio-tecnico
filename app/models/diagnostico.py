from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String, Text
from sqlalchemy.orm import deferred, relationship
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
    imagenes = relationship(
        "DiagnosticoImagen",
        back_populates="diagnostico",
        cascade="all, delete-orphan",
        order_by="DiagnosticoImagen.id",
    )
    mensaje_cliente = relationship(
        "DiagnosticoMensaje",
        back_populates="diagnostico",
        uselist=False,
        cascade="all, delete-orphan",
    )


class DiagnosticoImagen(Base):
    __tablename__ = "diagnostico_imagenes"

    id = Column(Integer, primary_key=True, index=True)
    diagnostico_id = Column(
        Integer,
        ForeignKey("diagnosticos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre_archivo = Column(String(255), nullable=False)
    tipo_contenido = Column(String(50), nullable=False)
    contenido = deferred(Column(LargeBinary, nullable=False))
    fecha_subida = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    diagnostico = relationship("Diagnostico", back_populates="imagenes")


class DiagnosticoMensaje(Base):
    __tablename__ = "diagnostico_mensajes"

    id = Column(Integer, primary_key=True, index=True)
    diagnostico_id = Column(Integer, ForeignKey("diagnosticos.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    mensaje = Column(Text, nullable=False)
    estado = Column(String(30), nullable=False, default="Pendiente", index=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    fecha_actualizacion = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    diagnostico = relationship("Diagnostico", back_populates="mensaje_cliente")
