from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import requiere
from ..models import Equipo, Evento, Sala, TicketAranda
from ..timeutil import a_local

router = APIRouter(prefix="/api", tags=["reportes y equipos"])


@router.get("/reportes/cifras")
def cifras(_=Depends(requiere("jefe_seguridad", "gestion_activos")), db: Session = Depends(get_db)):
    """HU-05: hurtos por sala y por mes, costo estimado acumulado y calidad de las alertas."""
    cfg = get_settings()
    eventos = list(db.scalars(select(Evento)))
    salas = {s.id: s for s in db.scalars(select(Sala))}
    confirmados = [e for e in eventos if e.estado == "confirmado"]

    por_sala_mes: dict[tuple[str, str], int] = defaultdict(int)
    for e in confirmados:
        por_sala_mes[(salas[e.sala_id].nombre, f"{a_local(e.ocurrido_en):%Y-%m}")] += 1

    por_sala: dict[str, int] = defaultdict(int)
    por_mes: dict[str, int] = defaultdict(int)
    for (sala, mes), n in por_sala_mes.items():
        por_sala[sala] += n
        por_mes[mes] += n

    revisados = [e for e in eventos if e.estado in ("confirmado", "descartado")]
    con_latencia = [e.latencia_seg for e in eventos if e.latencia_seg is not None]
    dentro_sla = [x for x in con_latencia if x <= cfg.sla_segundos]
    return {
        "total_alertas": len(eventos),
        "pendientes": sum(1 for e in eventos if e.estado == "pendiente"),
        "hurtos_confirmados": len(confirmados),
        "falsas_alarmas": sum(1 for e in eventos if e.estado == "descartado"),
        "porcentaje_falsas_alarmas": round(100 * (len(revisados) - len(confirmados)) / len(revisados), 1) if revisados else None,
        "costo_estimado_usd": round(len(confirmados) * cfg.costo_equipo_usd, 2),
        "costo_por_equipo_usd": cfg.costo_equipo_usd,
        "por_sala": [{"sala": s, "hurtos": n} for s, n in sorted(por_sala.items())],
        "por_mes": [{"mes": m, "hurtos": n} for m, n in sorted(por_mes.items())],
        "por_sala_y_mes": [{"sala": s, "mes": m, "hurtos": n} for (s, m), n in sorted(por_sala_mes.items())],
        "latencia": {
            "sla_segundos": cfg.sla_segundos,
            "alertas_medidas": len(con_latencia),
            "promedio_seg": round(sum(con_latencia) / len(con_latencia), 2) if con_latencia else None,
            "maxima_seg": round(max(con_latencia), 2) if con_latencia else None,
            "porcentaje_dentro_sla": round(100 * len(dentro_sla) / len(con_latencia), 1) if con_latencia else None,
        },
    }


@router.get("/salas")
def salas(_=Depends(requiere("guardia", "jefe_seguridad", "gestion_activos")), db: Session = Depends(get_db)):
    return [{"id": s.id, "nombre": s.nombre, "bloque": s.bloque} for s in db.scalars(select(Sala).order_by(Sala.nombre))]


@router.get("/equipos")
def equipos(_=Depends(requiere("guardia", "jefe_seguridad", "gestion_activos")), db: Session = Depends(get_db)):
    filas = db.execute(
        select(Equipo, Sala, TicketAranda).join(Sala, Equipo.sala_id == Sala.id).outerjoin(TicketAranda, Equipo.ticket_aranda_id == TicketAranda.id)
    )
    return [
        {
            "id": eq.id,
            "numero_serie": eq.numero_serie,
            "sala_id": sala.id,
            "sala": sala.nombre,
            "estado": eq.estado,
            "ticket": tk.numero if tk else None,
        }
        for eq, sala, tk in filas
    ]


@router.get("/publico/equipos/{numero_serie}")
def aviso_equipo(numero_serie: str, db: Session = Depends(get_db)):
    """HU-06: lo consulta el estudiante desde el QR del equipo. Sin datos personales y sin iniciar sesión."""
    fila = db.execute(
        select(Equipo, Sala, TicketAranda)
        .join(Sala, Equipo.sala_id == Sala.id)
        .outerjoin(TicketAranda, Equipo.ticket_aranda_id == TicketAranda.id)
        .where(Equipo.numero_serie == numero_serie)
    ).first()
    if fila is None:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    eq, sala, tk = fila
    con_falla = eq.estado != "activo" or (tk is not None and tk.estado != "Cerrado")
    return {
        "numero_serie": eq.numero_serie,
        "sala": sala.nombre,
        "con_falla_reportada": con_falla,
        "mensaje": (
            "Este equipo tiene un caso abierto en la mesa de servicio. Puede estar lento o incompleto; "
            "si puede, use otro equipo."
            if con_falla
            else "Este equipo no tiene casos abiertos. Si falla, repórtelo por el canal de Saúl."
        ),
        "ticket": tk.numero if tk else None,
    }
