"""Lógica de negocio de las alertas (HU-01, HU-02 y HU-04)."""
from datetime import datetime

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Equipo, Evento, Sala, Usuario
from ..timeutil import a_local, iso_utc, utcnow
from . import aranda_mock, storage
from .notifier import avisar_teams, difusor, texto_tipo


def evento_a_dict(ev: Evento, con_captura: bool = True) -> dict:
    sla = get_settings().sla_segundos
    return {
        "id": ev.id,
        "sala": {"id": ev.sala.id, "nombre": ev.sala.nombre, "bloque": ev.sala.bloque},
        "ocurrido_en": iso_utc(ev.ocurrido_en),
        "tipo": ev.tipo,
        "tipo_texto": texto_tipo(ev.tipo),
        "confianza": round(ev.confianza, 3),
        "estado": ev.estado,
        "captura_url": f"/api/eventos/{ev.id}/captura" if (con_captura and ev.captura_path) else None,
        "latencia_seg": None if ev.latencia_seg is None else round(ev.latencia_seg, 2),
        "cumple_sla": None if ev.latencia_seg is None else ev.latencia_seg <= sla,
        "notificado_teams": ev.notificado_teams,
        "ticket": ev.ticket.numero if ev.ticket else None,
        "equipo": ev.equipo.numero_serie if ev.equipo else None,
    }


def registrar_evento(
    db: Session, sala: Sala, tipo: str, confianza: float, ocurrido_en: datetime, captura: bytes | None
) -> Evento:
    """HU-01: guarda el evento, avisa por la app y por Teams, y mide el tiempo entre detección y aviso."""
    ev = Evento(sala_id=sala.id, tipo=tipo, confianza=confianza, ocurrido_en=ocurrido_en, recibido_en=utcnow())
    db.add(ev)
    db.flush()  # para tener el id
    if captura:
        ev.captura_path = storage.guardar_captura(ev.id, captura)
    db.commit()
    db.refresh(ev)

    hora_local = f"{a_local(ev.ocurrido_en):%d/%m/%Y %H:%M:%S}"
    ev.notificado_teams = avisar_teams(ev.id, sala.nombre, sala.bloque, tipo, hora_local, confianza)
    difusor.publicar({"tipo": "alerta", "evento": evento_a_dict(ev)})
    ev.notificado_en = utcnow()
    ev.latencia_seg = (ev.notificado_en - ev.ocurrido_en).total_seconds()
    db.commit()
    db.refresh(ev)
    return ev


def confirmar_hurto(db: Session, ev: Evento, usuario: Usuario, equipo_id: int | None) -> Evento:
    """HU-04: al confirmar, crea el ticket (simulado) y marca el equipo como pendiente de reposición."""
    equipo = None
    if equipo_id is not None:
        equipo = db.get(Equipo, equipo_id)
        if equipo is None or equipo.sala_id != ev.sala_id:
            raise ValueError("El equipo no existe o no pertenece a la sala del evento")
    ticket = aranda_mock.crear_ticket_incidente(db, ev, equipo)
    ev.estado = "confirmado"
    ev.ticket_id = ticket.id
    ev.revisado_por_id = usuario.id
    ev.revisado_en = utcnow()
    if equipo is not None:
        ev.equipo_id = equipo.id
        equipo.estado = "pendiente_reposicion"
        equipo.ticket_aranda_id = ticket.id
    db.commit()
    db.refresh(ev)
    return ev


def descartar_evento(db: Session, ev: Evento, usuario: Usuario) -> Evento:
    ev.estado = "descartado"
    ev.revisado_por_id = usuario.id
    ev.revisado_en = utcnow()
    db.commit()
    db.refresh(ev)
    return ev
