"""Páginas HTML. Los datos se piden por JavaScript a la API; aquí solo se controla el acceso por rol."""
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Usuario
from ..security import COOKIE, leer_sesion
from .auth import abrir_sesion, validar_credenciales

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
router = APIRouter(include_in_schema=False)

SEGURIDAD = ("guardia", "jefe_seguridad")
TODOS = ("guardia", "jefe_seguridad", "gestion_activos")


class RedirigirA(Exception):
    def __init__(self, destino: str):
        self.destino = destino


def pagina(*roles: str):
    """Exige sesión y rol. Sin sesión va al login; con un rol sin permiso, al historial."""

    def dependencia(request: Request, db: Session = Depends(get_db)) -> Usuario:
        valor = request.cookies.get(COOKIE)
        uid = leer_sesion(valor) if valor else None
        usuario = db.get(Usuario, uid) if uid else None
        if usuario is None:
            raise RedirigirA("/login")
        if usuario.rol not in roles:
            raise RedirigirA("/historial")
        return usuario

    return dependencia


def _render(request: Request, plantilla: str, usuario: Usuario | None, activa: str = "", **extra):
    contexto = {"usuario": usuario, "activa": activa, **extra}
    return templates.TemplateResponse(request, plantilla, contexto)


def _inicio(usuario: Usuario) -> str:
    return "/alertas" if usuario.rol in SEGURIDAD else "/panel"


@router.get("/")
def raiz(request: Request, db: Session = Depends(get_db)):
    valor = request.cookies.get(COOKIE)
    uid = leer_sesion(valor) if valor else None
    usuario = db.get(Usuario, uid) if uid else None
    return RedirectResponse(_inicio(usuario) if usuario else "/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_pagina(request: Request):
    return _render(request, "login.html", None, error=None)


@router.post("/login")
def login_envio(request: Request, correo: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    try:
        usuario = validar_credenciales(db, correo, password)
    except HTTPException:
        return _render(request, "login.html", None, error="Correo o contraseña incorrectos")
    respuesta = RedirectResponse(_inicio(usuario), status_code=303)
    abrir_sesion(respuesta, usuario)
    return respuesta


@router.post("/salir")
def salir():
    respuesta = RedirectResponse("/login", status_code=303)
    respuesta.delete_cookie(COOKIE)
    return respuesta


@router.get("/alertas", response_class=HTMLResponse)
def alertas(request: Request, usuario: Usuario = Depends(pagina(*SEGURIDAD))):
    return _render(request, "alertas.html", usuario, "alertas")


@router.get("/historial", response_class=HTMLResponse)
def historial(request: Request, usuario: Usuario = Depends(pagina(*TODOS))):
    return _render(request, "historial.html", usuario, "historial")


@router.get("/evento/{evento_id}", response_class=HTMLResponse)
def evento(evento_id: int, request: Request, usuario: Usuario = Depends(pagina(*TODOS))):
    return _render(request, "evento.html", usuario, "historial", evento_id=evento_id, puede_decidir=usuario.rol in SEGURIDAD)


@router.get("/panel", response_class=HTMLResponse)
def panel(request: Request, usuario: Usuario = Depends(pagina("jefe_seguridad", "gestion_activos"))):
    return _render(request, "panel.html", usuario, "panel")


@router.get("/equipos", response_class=HTMLResponse)
def equipos(request: Request, usuario: Usuario = Depends(pagina(*TODOS))):
    return _render(request, "equipos.html", usuario, "equipos")


@router.get("/aviso/{numero_serie}", response_class=HTMLResponse)
def aviso(numero_serie: str, request: Request):
    """Página pública del QR del equipo (HU-06). No pide sesión y no muestra datos personales."""
    return _render(request, "aviso.html", None, numero_serie=numero_serie)
