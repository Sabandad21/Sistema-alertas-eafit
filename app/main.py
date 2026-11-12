from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import Base, engine
from .routers import auth, eventos, reportes, web


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="Sistema de Alertas EAFIT",
    description="Alertas de seguridad para las salas de cómputo (prototipo de la entrega 3).",
    version="0.1.0",
    lifespan=ciclo_de_vida,
)

app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")
app.include_router(auth.router)
app.include_router(eventos.router)
app.include_router(reportes.router)
app.include_router(web.router)


@app.exception_handler(web.RedirigirA)
async def redirigir(_: Request, error: web.RedirigirA):
    return RedirectResponse(error.destino, status_code=303)


CABECERAS = {
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
}


@app.middleware("http")
async def cabeceras_de_seguridad(request: Request, siguiente):
    respuesta = await siguiente(request)
    for nombre, valor in CABECERAS.items():
        respuesta.headers.setdefault(nombre, valor)
    if get_settings().app_env == "prod":
        respuesta.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return respuesta


@app.get("/salud", tags=["operación"])
def salud():
    """Lo usan el despliegue y el monitoreo para saber si el servicio responde."""
    return {"estado": "ok"}
