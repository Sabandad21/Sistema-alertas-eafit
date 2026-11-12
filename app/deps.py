import hmac

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import Auditoria, Usuario
from .security import COOKIE, leer_sesion


def usuario_actual(request: Request, db: Session = Depends(get_db)) -> Usuario:
    valor = request.cookies.get(COOKIE)
    uid = leer_sesion(valor) if valor else None
    usuario = db.get(Usuario, uid) if uid else None
    if usuario is None:
        raise HTTPException(status_code=401, detail="Debe iniciar sesión")
    return usuario


def requiere(*roles: str):
    def dependencia(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(status_code=403, detail="No tiene permiso para esta acción")
        return usuario

    return dependencia


def verificar_api_key(x_api_key: str = Header(default="")) -> None:
    clave = get_settings().detector_api_key
    if not clave or not hmac.compare_digest(x_api_key, clave):
        raise HTTPException(status_code=401, detail="API key inválida")


def registrar_consulta(db: Session, usuario: Usuario, accion: str, recurso: str) -> None:
    db.add(Auditoria(usuario_id=usuario.id, accion=accion, recurso=recurso))
    db.commit()
