"""Datos de PRUEBA creados por el equipo. No contienen información real de EAFIT."""
import random
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Equipo, Evento, Sala, Usuario
from .security import hash_password
from .services import aranda_mock
from .timeutil import utcnow

SALAS = [
    ("Sala de prueba A", "Bloque de prueba 1"),
    ("Sala de prueba B", "Bloque de prueba 1"),
    ("Sala de prueba C", "Bloque de prueba 2"),
]
USUARIOS = [
    ("Guardia de prueba", "guardia@prueba.local", "guardia"),
    ("Jefe de seguridad de prueba", "jefe@prueba.local", "jefe_seguridad"),
    ("Gestión de Activos de prueba", "activos@prueba.local", "gestion_activos"),
]
TIPOS = ["equipo_retirado", "permanencia_prolongada", "presencia_fuera_de_horario"]


def sembrar(db: Session, password: str, historial: bool = False) -> bool:
    """Crea salas, equipos y usuarios de prueba. Devuelve False si la base ya tenía datos."""
    if db.scalar(select(Sala).limit(1)) is not None:
        return False
    salas = [Sala(nombre=n, bloque=b) for n, b in SALAS]
    db.add_all(salas)
    db.flush()
    for letra, sala in zip("ABC", salas):
        db.add_all([Equipo(sala_id=sala.id, numero_serie=f"TEST-{letra}-{i:03d}") for i in range(1, 7)])
    clave = hash_password(password)
    db.add_all([Usuario(nombre=n, correo=c, rol=r, password_hash=clave) for n, c, r in USUARIOS])
    db.commit()
    if historial:
        _sembrar_historial(db, salas)
    return True


def _sembrar_historial(db: Session, salas: list[Sala], semilla: int = 7) -> None:
    """~35 eventos de los últimos 6 meses para que el panel de cifras tenga algo que mostrar."""
    azar = random.Random(semilla)
    ahora = utcnow()
    jefe = db.scalar(select(Usuario).where(Usuario.rol == "jefe_seguridad"))
    for _ in range(35):
        momento = ahora - timedelta(days=azar.randint(3, 180), hours=azar.randint(0, 23), minutes=azar.randint(0, 59))
        sala = azar.choice(salas)
        estado = azar.choices(["confirmado", "descartado"], weights=[65, 35])[0]
        ev = Evento(
            sala_id=sala.id,
            tipo=azar.choice(TIPOS),
            confianza=round(azar.uniform(0.55, 0.95), 3),
            ocurrido_en=momento,
            recibido_en=momento + timedelta(seconds=1),
            estado=estado,
            latencia_seg=round(azar.uniform(2, 18), 2),
            notificado_en=momento + timedelta(seconds=5),
            revisado_por_id=jefe.id,
            revisado_en=momento + timedelta(minutes=azar.randint(2, 30)),
        )
        db.add(ev)
        db.flush()
        if estado == "confirmado":
            ev.ticket_id = aranda_mock.crear_ticket_incidente(db, ev, None).id
    db.commit()
