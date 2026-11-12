import asyncio
import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import registrar_consulta, requiere, usuario_actual, verificar_api_key
from ..models import ESTADOS_EVENTO, Evento, Sala, Usuario
from ..services import eventos as servicio
from ..services import storage
from ..services.notifier import difusor
from ..timeutil import a_utc_naive, fin_dia_local_a_utc, inicio_dia_local_a_utc

router = APIRouter(prefix="/api", tags=["eventos"])

SEGURIDAD = ("guardia", "jefe_seguridad")
TODOS = ("guardia", "jefe_seguridad", "gestion_activos")


@router.post("/eventos", status_code=201, dependencies=[Depends(verificar_api_key)])
async def crear_evento(
    sala_id: int = Form(...),
    tipo: str = Form(...),
    confianza: float = Form(..., ge=0, le=1),
    ocurrido_en: str = Form(..., description="Fecha y hora ISO 8601 en que el detector disparó la regla"),
    captura: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    """Lo llama el detector (HU-01). Se protege con la cabecera X-API-Key."""
    sala = db.get(Sala, sala_id)
    if sala is None:
        raise HTTPException(status_code=404, detail="La sala no existe")
    try:
        momento = a_utc_naive(datetime.fromisoformat(ocurrido_en.replace("Z", "+00:00")))
    except ValueError:
        raise HTTPException(status_code=422, detail="ocurrido_en debe ser una fecha ISO 8601")
    datos = await captura.read() if captura else None
    try:
        ev = servicio.registrar_evento(db, sala, tipo, confianza, momento, datos)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return servicio.evento_a_dict(ev)


@router.get("/eventos")
def listar_eventos(
    sala_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    estado: str | None = None,
    limite: int = Query(100, ge=1, le=500),
    usuario: Usuario = Depends(requiere(*TODOS)),
    db: Session = Depends(get_db),
):
    """HU-02: historial con filtros por sala, rango de fechas y estado."""
    if estado is not None and estado not in ESTADOS_EVENTO:
        raise HTTPException(status_code=422, detail=f"estado debe ser uno de {ESTADOS_EVENTO}")
    consulta = select(Evento).order_by(Evento.ocurrido_en.desc()).limit(limite)
    if sala_id is not None:
        consulta = consulta.where(Evento.sala_id == sala_id)
    if desde is not None:
        consulta = consulta.where(Evento.ocurrido_en >= inicio_dia_local_a_utc(desde))
    if hasta is not None:
        consulta = consulta.where(Evento.ocurrido_en <= fin_dia_local_a_utc(hasta))
    if estado is not None:
        consulta = consulta.where(Evento.estado == estado)
    registrar_consulta(db, usuario, "consulta_historial", f"sala={sala_id} desde={desde} hasta={hasta} estado={estado}")
    # Gestión de Activos ve el historial pero no las capturas (solo Seguridad).
    con_captura = usuario.rol in SEGURIDAD
    return [servicio.evento_a_dict(ev, con_captura) for ev in db.scalars(consulta)]


def _evento_o_404(db: Session, evento_id: int) -> Evento:
    ev = db.get(Evento, evento_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="El evento no existe")
    return ev


@router.get("/eventos/{evento_id}")
def ver_evento(evento_id: int, usuario: Usuario = Depends(requiere(*TODOS)), db: Session = Depends(get_db)):
    ev = _evento_o_404(db, evento_id)
    registrar_consulta(db, usuario, "consulta_evento", f"evento={evento_id}")
    return servicio.evento_a_dict(ev, usuario.rol in SEGURIDAD)


@router.get("/eventos/{evento_id}/captura")
def ver_captura(evento_id: int, usuario: Usuario = Depends(requiere(*SEGURIDAD)), db: Session = Depends(get_db)):
    ev = _evento_o_404(db, evento_id)
    ruta = storage.ruta_captura(ev.captura_path) if ev.captura_path else None
    if ruta is None:
        raise HTTPException(status_code=404, detail="El evento no tiene captura")
    registrar_consulta(db, usuario, "consulta_captura", f"evento={evento_id}")
    return FileResponse(ruta)


class ConfirmarIn(BaseModel):
    equipo_id: int | None = None


@router.post("/eventos/{evento_id}/confirmar")
def confirmar(
    evento_id: int,
    datos: ConfirmarIn | None = None,
    usuario: Usuario = Depends(requiere(*SEGURIDAD)),
    db: Session = Depends(get_db),
):
    ev = _evento_o_404(db, evento_id)
    if ev.estado != "pendiente":
        raise HTTPException(status_code=409, detail=f"El evento ya fue {ev.estado}")
    try:
        ev = servicio.confirmar_hurto(db, ev, usuario, datos.equipo_id if datos else None)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return servicio.evento_a_dict(ev)


@router.post("/eventos/{evento_id}/descartar")
def descartar(evento_id: int, usuario: Usuario = Depends(requiere(*SEGURIDAD)), db: Session = Depends(get_db)):
    ev = _evento_o_404(db, evento_id)
    if ev.estado != "pendiente":
        raise HTTPException(status_code=409, detail=f"El evento ya fue {ev.estado}")
    return servicio.evento_a_dict(servicio.descartar_evento(db, ev, usuario))


@router.get("/alertas/stream")
async def alertas_en_vivo(request: Request, usuario: Usuario = Depends(requiere(*SEGURIDAD))):
    """Flujo de eventos en vivo (Server-Sent Events) para la pantalla del guardia."""
    cola = difusor.suscribir()

    async def generador():
        try:
            yield "retry: 3000\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    mensaje = await asyncio.wait_for(cola.get(), timeout=15)
                    yield f"data: {json.dumps(mensaje)}\n\n"
                except asyncio.TimeoutError:
                    yield ": latido\n\n"
        finally:
            difusor.cancelar(cola)

    return StreamingResponse(generador(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
