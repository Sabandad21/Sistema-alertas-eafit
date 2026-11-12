"""Manejo de fechas: todo se guarda en UTC (sin zona) y se muestra en hora de Bogotá (UTC-5, sin horario de verano)."""
from datetime import date, datetime, time, timedelta, timezone

BOGOTA = timezone(timedelta(hours=-5))


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def a_utc_naive(valor: datetime) -> datetime:
    """Convierte cualquier datetime a UTC sin zona. Si no trae zona se asume UTC."""
    if valor.tzinfo is None:
        return valor
    return valor.astimezone(timezone.utc).replace(tzinfo=None)


def a_local(valor: datetime) -> datetime:
    """UTC sin zona -> hora de Bogotá (con zona)."""
    return valor.replace(tzinfo=timezone.utc).astimezone(BOGOTA)


def iso_utc(valor: datetime | None) -> str | None:
    return None if valor is None else valor.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def inicio_dia_local_a_utc(dia: date) -> datetime:
    return a_utc_naive(datetime.combine(dia, time.min, tzinfo=BOGOTA))


def fin_dia_local_a_utc(dia: date) -> datetime:
    return a_utc_naive(datetime.combine(dia, time.max, tzinfo=BOGOTA))
