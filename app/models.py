"""Modelo de datos (Tabla 13 de la entrega 2, más tickets simulados y bitácora de consultas)."""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .timeutil import utcnow

ROLES = ("guardia", "jefe_seguridad", "gestion_activos")
ESTADOS_EVENTO = ("pendiente", "confirmado", "descartado")


class Sala(Base):
    __tablename__ = "salas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    bloque: Mapped[str] = mapped_column(String(40))
    camara_activa: Mapped[bool] = mapped_column(default=True)
    equipos: Mapped[list["Equipo"]] = relationship(back_populates="sala")


class TicketAranda(Base):
    """Ticket SIMULADO con los mismos campos que usa Aranda. No se conecta al Aranda real."""
    __tablename__ = "tickets_aranda"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero: Mapped[str] = mapped_column(String(30), unique=True)
    proyecto: Mapped[str] = mapped_column(String(30))
    servicio: Mapped[str] = mapped_column(String(80))
    categoria: Mapped[str] = mapped_column(String(80))
    descripcion: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(20), default="Abierto")
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Equipo(Base):
    __tablename__ = "equipos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sala_id: Mapped[int] = mapped_column(ForeignKey("salas.id"))
    numero_serie: Mapped[str] = mapped_column(String(40), unique=True)
    estado: Mapped[str] = mapped_column(String(30), default="activo")  # activo | pendiente_reposicion
    ticket_aranda_id: Mapped[int | None] = mapped_column(ForeignKey("tickets_aranda.id"), nullable=True)
    sala: Mapped[Sala] = relationship(back_populates="equipos")
    ticket: Mapped[TicketAranda | None] = relationship()


class Usuario(Base):
    __tablename__ = "usuarios_seguridad"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    correo: Mapped[str] = mapped_column(String(120), unique=True)
    rol: Mapped[str] = mapped_column(String(30))
    password_hash: Mapped[str] = mapped_column(String(200))


class Evento(Base):
    __tablename__ = "eventos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sala_id: Mapped[int] = mapped_column(ForeignKey("salas.id"), index=True)
    ocurrido_en: Mapped[datetime] = mapped_column(DateTime, index=True)  # momento en que el detector disparó la regla
    recibido_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    notificado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    latencia_seg: Mapped[float | None] = mapped_column(Float, nullable=True)  # notificado_en - ocurrido_en
    tipo: Mapped[str] = mapped_column(String(40))
    confianza: Mapped[float] = mapped_column(Float)
    estado: Mapped[str] = mapped_column(String(20), default="pendiente", index=True)
    captura_path: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notificado_teams: Mapped[bool] = mapped_column(default=False)
    equipo_id: Mapped[int | None] = mapped_column(ForeignKey("equipos.id"), nullable=True)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets_aranda.id"), nullable=True)
    revisado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios_seguridad.id"), nullable=True)
    revisado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    sala: Mapped[Sala] = relationship()
    equipo: Mapped[Equipo | None] = relationship()
    ticket: Mapped[TicketAranda | None] = relationship()
    revisado_por: Mapped[Usuario | None] = relationship()


class Auditoria(Base):
    """Cada consulta a eventos o capturas queda registrada (decisión de privacidad nº 3)."""
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios_seguridad.id"))
    accion: Mapped[str] = mapped_column(String(40))
    recurso: Mapped[str] = mapped_column(String(120))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
