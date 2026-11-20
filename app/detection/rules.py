"""Reglas de comportamiento sospechoso sobre las detecciones de un modelo de visión (YOLOv8).

El modelo solo reconoce objetos comunes (persona, portátil, teclado...). NO existe un modelo que
reconozca "abrir una torre" o "robar RAM". Por eso el comportamiento se define con dos reglas
simples sobre lo que el modelo sí ve:

  1. equipo_retirado: un portátil que se veía estable desaparece mientras hay una persona en cuadro.
  2. presencia_fuera_de_horario: hay una persona en la sala fuera del horario de ocupación.

Estar cerca de un equipo NO es sospechoso: en una sala de cómputo los estudiantes usan los equipos todo el
día. Por eso no hay una regla de "permanencia junto al equipo" (la tuvo la primera versión del prototipo y se
retiró). Abrir o destapar un equipo no se puede detectar con un modelo preentrenado; queda como trabajo futuro.

Este módulo no depende de OpenCV ni de la red: recibe detecciones y tiempos, y devuelve eventos.
Así se puede probar con secuencias sintéticas.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

PERSONA = "person"
PORTATIL = "laptop"

BOGOTA = timezone(timedelta(hours=-5))


@dataclass(frozen=True)
class Deteccion:
    clase: str
    confianza: float
    caja: tuple[float, float, float, float]  # x1, y1, x2, y2 en píxeles


@dataclass(frozen=True)
class EventoDetectado:
    tipo: str
    confianza: float
    ts: float  # segundos epoch en que se disparó la regla
    detalle: str


@dataclass
class ReglasConfig:
    min_confianza: float = 0.40
    equipo_estable_seg: float = 3.0  # un portátil cuenta como "presente" tras verse así de tiempo
    equipo_ausente_seg: float = 3.0  # y como "retirado" si falta este tiempo
    persona_reciente_seg: float = 6.0  # con una persona vista en los últimos segundos
    fuera_horario_seg: float = 5.0
    hora_inicio_ocupacion: int = 6  # ocupación normal: 06:00 a 22:00
    hora_fin_ocupacion: int = 22
    hora_fija: int | None = None  # para simular una hora en las pruebas y en la demo
    cooldown_seg: float = 60.0  # no repite el mismo tipo de evento antes de este tiempo
    tolerancia_hueco_seg: float = 1.0  # huecos cortos del detector no reinician la cuenta


def _hora_local(ts: float) -> int:
    return datetime.fromtimestamp(ts, tz=BOGOTA).hour


class MotorReglas:
    def __init__(self, config: ReglasConfig | None = None, reloj_hora: Callable[[float], int] = _hora_local):
        self.cfg = config or ReglasConfig()
        self._hora = reloj_hora
        # equipo retirado
        self._base_portatiles = 0
        self._conteo_actual = None
        self._conteo_desde = 0.0
        self._ultima_persona = None
        self._menos_desde = None
        # fuera de horario: [inicio, ultimo_visto]
        self._fuera: list[float] | None = None
        self._fuera_conf: list[float] = []
        self._ultimo_evento: dict[str, float] = defaultdict(lambda: -1e18)

    # -- utilidades ------------------------------------------------------
    def _puede(self, tipo: str, ts: float) -> bool:
        return ts - self._ultimo_evento[tipo] >= self.cfg.cooldown_seg

    def _emitir(self, salida: list, tipo: str, conf: float, ts: float, detalle: str) -> None:
        if self._puede(tipo, ts):
            self._ultimo_evento[tipo] = ts
            salida.append(EventoDetectado(tipo, round(conf, 3), ts, detalle))

    def _fuera_de_horario(self, ts: float) -> bool:
        hora = self.cfg.hora_fija if self.cfg.hora_fija is not None else self._hora(ts)
        return not (self.cfg.hora_inicio_ocupacion <= hora < self.cfg.hora_fin_ocupacion)

    # -- procesamiento ---------------------------------------------------
    def procesar(self, ts: float, detecciones: list[Deteccion]) -> list[EventoDetectado]:
        c = self.cfg
        validas = [d for d in detecciones if d.confianza >= c.min_confianza]
        personas = [d for d in validas if d.clase == PERSONA]
        portatiles = [d for d in validas if d.clase == PORTATIL]
        salida: list[EventoDetectado] = []

        if personas:
            self._ultima_persona = ts

        self._regla_equipo_retirado(ts, portatiles, salida)
        self._regla_fuera_horario(ts, personas, salida)
        return salida

    def _regla_equipo_retirado(self, ts, portatiles, salida) -> None:
        c = self.cfg
        n = len(portatiles)
        if n != self._conteo_actual:
            self._conteo_actual, self._conteo_desde = n, ts
        # El conteo estable se vuelve la referencia ("lo normal en esta sala").
        if ts - self._conteo_desde >= c.equipo_estable_seg and n >= self._base_portatiles:
            self._base_portatiles = n
        if n < self._base_portatiles:
            if self._menos_desde is None:
                self._menos_desde = ts
            persona_cerca = self._ultima_persona is not None and ts - self._ultima_persona <= c.persona_reciente_seg
            if ts - self._menos_desde >= c.equipo_ausente_seg and persona_cerca:
                conf = 0.6 + 0.4 * min(1.0, (ts - self._menos_desde) / (3 * c.equipo_ausente_seg))
                self._emitir(salida, "equipo_retirado", conf, ts, f"Se veían {self._base_portatiles} portátiles y ahora {n}")
                self._base_portatiles = n  # la nueva referencia, para no repetir el evento
                self._menos_desde = None
        else:
            self._menos_desde = None

    def _acumular(self, estado, ts, activo: bool, confs: list, conf: float):
        """Mantiene un intervalo continuo [inicio, último_visto] tolerando huecos cortos. Devuelve la duración o 0."""
        c = self.cfg
        if activo:
            if estado is None or ts - estado[1] > c.tolerancia_hueco_seg:
                estado = [ts, ts]
                confs.clear()
            estado[1] = ts
            confs.append(conf)
            return estado, ts - estado[0]
        if estado is not None and ts - estado[1] > c.tolerancia_hueco_seg:
            confs.clear()
            return None, 0.0
        return estado, 0.0

    def _regla_fuera_horario(self, ts, personas, salida) -> None:
        activo = bool(personas) and self._fuera_de_horario(ts)
        conf = max((p.confianza for p in personas), default=0.0)
        self._fuera, dur = self._acumular(self._fuera, ts, activo, self._fuera_conf, conf)
        if dur >= self.cfg.fuera_horario_seg:
            media = sum(self._fuera_conf) / len(self._fuera_conf)
            self._emitir(salida, "presencia_fuera_de_horario", media, ts, f"Persona en la sala fuera de horario durante {dur:.0f} s")
