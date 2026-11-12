"""Notificaciones: alerta en vivo dentro de la app (SSE) y aviso a Microsoft Teams por webhook."""
import asyncio
import logging
import threading

import httpx

from ..config import get_settings

log = logging.getLogger("alertas.notifier")

TIPOS_TEXTO = {
    "equipo_retirado": "Equipo retirado de la sala",
    "permanencia_prolongada": "Permanencia prolongada junto a un equipo",
    "presencia_fuera_de_horario": "Presencia fuera de horario",
    "simulado": "Evento simulado (prueba)",
}


def texto_tipo(tipo: str) -> str:
    return TIPOS_TEXTO.get(tipo, tipo)


class Difusor:
    """Reparte los eventos a las pantallas abiertas. Funciona con un solo proceso (suficiente para el piloto)."""

    def __init__(self) -> None:
        self._suscriptores: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []
        self._lock = threading.Lock()

    def suscribir(self) -> asyncio.Queue:
        cola: asyncio.Queue = asyncio.Queue(maxsize=100)
        with self._lock:
            self._suscriptores.append((asyncio.get_running_loop(), cola))
        return cola

    def cancelar(self, cola: asyncio.Queue) -> None:
        with self._lock:
            self._suscriptores = [(lp, q) for lp, q in self._suscriptores if q is not cola]

    def publicar(self, mensaje: dict) -> int:
        with self._lock:
            destinos = list(self._suscriptores)
        for loop, cola in destinos:
            try:
                loop.call_soon_threadsafe(cola.put_nowait, mensaje)
            except Exception:  # cola llena o loop cerrado
                log.warning("No se pudo entregar la alerta a un suscriptor")
        return len(destinos)


difusor = Difusor()


def avisar_teams(evento_id: int, sala: str, bloque: str, tipo: str, hora_local: str, confianza: float) -> bool:
    """Envía una tarjeta a Teams. Devuelve True si el webhook respondió bien. Sin webhook configurado, no hace nada."""
    cfg = get_settings()
    if not cfg.teams_webhook_url:
        return False
    enlace = f"{cfg.app_base_url}/evento/{evento_id}"
    tarjeta = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {"type": "TextBlock", "text": "Alerta de seguridad en sala de cómputo", "weight": "Bolder", "size": "Medium"},
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "Sala", "value": f"{sala} ({bloque})"},
                                {"title": "Hora", "value": hora_local},
                                {"title": "Evento", "value": texto_tipo(tipo)},
                                {"title": "Confianza", "value": f"{confianza:.0%}"},
                            ],
                        },
                    ],
                    "actions": [{"type": "Action.OpenUrl", "title": "Revisar alerta", "url": enlace}],
                },
            }
        ],
    }
    try:
        respuesta = httpx.post(cfg.teams_webhook_url, json=tarjeta, timeout=5.0)
        return respuesta.status_code < 300
    except httpx.HTTPError as error:
        log.warning("No se pudo avisar a Teams: %s", error)
        return False
