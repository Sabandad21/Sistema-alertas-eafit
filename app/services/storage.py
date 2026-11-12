"""Almacenamiento de capturas. En local usa disco; en Azure se puede cambiar por Blob Storage sin tocar el resto."""
import os

from ..config import get_settings

MAX_BYTES = 2 * 1024 * 1024


def _es_imagen(datos: bytes) -> bool:
    return datos.startswith(b"\xff\xd8\xff") or datos.startswith(b"\x89PNG\r\n\x1a\n")


def guardar_captura(evento_id: int, datos: bytes) -> str:
    if len(datos) > MAX_BYTES:
        raise ValueError("La captura supera 2 MB")
    if not _es_imagen(datos):
        raise ValueError("La captura debe ser JPEG o PNG")
    carpeta = get_settings().capturas_dir
    os.makedirs(carpeta, exist_ok=True)
    extension = "png" if datos.startswith(b"\x89PNG") else "jpg"
    nombre = f"evento_{evento_id}.{extension}"
    with open(os.path.join(carpeta, nombre), "wb") as archivo:
        archivo.write(datos)
    return nombre


def ruta_captura(nombre: str) -> str | None:
    # basename evita salirse de la carpeta de capturas
    ruta = os.path.join(get_settings().capturas_dir, os.path.basename(nombre))
    return ruta if os.path.isfile(ruta) else None
