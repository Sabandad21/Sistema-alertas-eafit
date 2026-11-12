import base64
import hashlib
import hmac
import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import get_settings

COOKIE = "sesion"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, almacenado: str) -> bool:
    try:
        esquema, salt_b64, hash_b64 = almacenado.split("$")
        if esquema != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        esperado = base64.b64decode(hash_b64)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(digest, esperado)
    except Exception:
        return False


def _serializador() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt="sesion-alertas")


def crear_sesion(usuario_id: int) -> str:
    return _serializador().dumps({"uid": usuario_id})


def leer_sesion(valor: str) -> int | None:
    try:
        datos = _serializador().loads(valor, max_age=get_settings().sesion_horas * 3600)
        return int(datos["uid"])
    except (BadSignature, SignatureExpired, KeyError, ValueError):
        return None
