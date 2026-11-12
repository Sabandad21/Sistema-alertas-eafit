import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def _normalizar(url: str) -> str:
    # Azure y otros proveedores entregan "postgres://" o "postgresql://"; SQLAlchemy necesita el driver.
    for prefijo in ("postgres://", "postgresql://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg://" + url[len(prefijo):]
    return url


_url = _normalizar(get_settings().database_url)
_args = {}
if _url.startswith("sqlite"):
    _args = {"check_same_thread": False}
    ruta = _url.replace("sqlite:///", "", 1)
    if ruta and ruta != ":memory:" and os.path.dirname(ruta):
        os.makedirs(os.path.dirname(ruta), exist_ok=True)

engine = create_engine(_url, connect_args=_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
