"""Configuración leída solo de variables de entorno.

Ningún secreto vive en el código: SECRET_KEY, DETECTOR_API_KEY, TEAMS_WEBHOOK_URL y
DATABASE_URL se definen en el ambiente (ver .env.example).
"""
import os
import secrets
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    app_env: str
    app_base_url: str
    database_url: str
    secret_key: str
    detector_api_key: str
    teams_webhook_url: str
    capturas_dir: str
    sla_segundos: int
    costo_equipo_usd: float
    sesion_horas: int


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "dev"),
        app_base_url=os.getenv("APP_BASE_URL", "http://localhost:8000").rstrip("/"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/alertas.db"),
        # Si no se define, se genera una clave por proceso (las sesiones no sobreviven a un reinicio).
        secret_key=os.getenv("SECRET_KEY") or secrets.token_urlsafe(32),
        # Sin clave, el endpoint que usa el detector queda cerrado.
        detector_api_key=os.getenv("DETECTOR_API_KEY", ""),
        teams_webhook_url=os.getenv("TEAMS_WEBHOOK_URL", ""),
        capturas_dir=os.getenv("CAPTURAS_DIR", "./data/capturas"),
        sla_segundos=int(os.getenv("SLA_ALERTA_SEGUNDOS", "30")),
        costo_equipo_usd=float(os.getenv("COSTO_EQUIPO_USD", "1800")),
        sesion_horas=int(os.getenv("SESION_HORAS", "8")),
    )
