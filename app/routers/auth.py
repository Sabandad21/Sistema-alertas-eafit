from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import usuario_actual
from ..models import Usuario
from ..security import COOKIE, crear_sesion, verify_password

router = APIRouter(prefix="/api", tags=["autenticación"])


class LoginIn(BaseModel):
    correo: str
    password: str


def abrir_sesion(respuesta: Response, usuario: Usuario) -> None:
    cfg = get_settings()
    respuesta.set_cookie(
        COOKIE,
        crear_sesion(usuario.id),
        max_age=cfg.sesion_horas * 3600,
        httponly=True,
        samesite="lax",
        secure=cfg.app_env == "prod",
    )


def validar_credenciales(db: Session, correo: str, password: str) -> Usuario:
    usuario = db.scalar(select(Usuario).where(Usuario.correo == correo.strip().lower()))
    # Mismo mensaje para correo inexistente y clave errónea, para no revelar qué usuarios existen.
    if usuario is None or not verify_password(password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    return usuario


@router.post("/login")
def login(datos: LoginIn, respuesta: Response, db: Session = Depends(get_db)):
    usuario = validar_credenciales(db, datos.correo, datos.password)
    abrir_sesion(respuesta, usuario)
    return {"nombre": usuario.nombre, "rol": usuario.rol}


@router.post("/logout")
def logout(respuesta: Response):
    respuesta.delete_cookie(COOKIE)
    return {"ok": True}


@router.get("/yo")
def yo(usuario: Usuario = Depends(usuario_actual)):
    return {"nombre": usuario.nombre, "correo": usuario.correo, "rol": usuario.rol}
