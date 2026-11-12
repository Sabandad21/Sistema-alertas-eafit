"""Cliente SIMULADO de Aranda.

Genera el ticket de incidente con los mismos campos que se vieron en el formulario real de Aranda
(proyecto SAUL, servicio Gestión de incidentes, categoría Mesa de servicio incidente), pero lo guarda
en la base de datos propia. No llama al Aranda real: la integración real queda pendiente de que
Gestión de Activos confirme si hay API o ambiente de pruebas.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Equipo, Evento, TicketAranda
from ..timeutil import a_local

PROYECTO = "SAUL"
SERVICIO = "Gestión de incidentes"
CATEGORIA = "Mesa de servicio incidente"


def crear_ticket_incidente(db: Session, evento: Evento, equipo: Equipo | None) -> TicketAranda:
    consecutivo = (db.scalar(select(func.count(TicketAranda.id))) or 0) + 1
    anio = a_local(evento.ocurrido_en).year
    detalle_equipo = f" Equipo afectado: {equipo.numero_serie}." if equipo else ""
    ticket = TicketAranda(
        numero=f"SAUL-{anio}-{consecutivo:05d}",
        proyecto=PROYECTO,
        servicio=SERVICIO,
        categoria=CATEGORIA,
        descripcion=(
            f"Hurto confirmado por Seguridad en {evento.sala.nombre} ({evento.sala.bloque}). "
            f"Detectado el {a_local(evento.ocurrido_en):%d/%m/%Y %H:%M}. "
            f"Tipo de evento: {evento.tipo}.{detalle_equipo}"
        ),
    )
    db.add(ticket)
    db.flush()
    return ticket
