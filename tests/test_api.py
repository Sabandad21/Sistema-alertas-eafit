"""Pruebas de aceptación de HU-01, HU-02, HU-04, HU-05 y HU-06, y de seguridad básica."""
from datetime import timedelta

from sqlalchemy import select

from app.models import Auditoria, Equipo, Sala
from app.timeutil import iso_utc, utcnow

from .conftest import API_KEY, iniciar_sesion

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64


def disparar(cliente, sala_id=1, hace_seg=1.0, tipo="equipo_retirado", captura=True):
    ocurrido = iso_utc(utcnow() - timedelta(seconds=hace_seg))
    archivos = {"captura": ("captura.jpg", JPEG, "image/jpeg")} if captura else None
    return cliente.post(
        "/api/eventos",
        data={"sala_id": sala_id, "tipo": tipo, "confianza": 0.87, "ocurrido_en": ocurrido},
        files=archivos,
        headers={"X-API-Key": API_KEY},
    )


# --- HU-01 -----------------------------------------------------------------
def test_hu01_alerta_incluye_sala_fecha_hora_captura_y_queda_en_historial(cliente):
    r = disparar(cliente)
    assert r.status_code == 201
    ev = r.json()
    assert ev["sala"]["nombre"] and ev["ocurrido_en"] and ev["captura_url"]
    iniciar_sesion(cliente, "guardia@prueba.local")
    historial = cliente.get("/api/eventos").json()
    assert [e["id"] for e in historial] == [ev["id"]]


def test_hu01_notificacion_en_menos_de_30_segundos(cliente):
    ev = disparar(cliente, hace_seg=2.0).json()
    assert ev["latencia_seg"] is not None
    assert ev["latencia_seg"] < 30 and ev["cumple_sla"] is True


def test_detector_sin_api_key_es_rechazado(cliente):
    r = cliente.post("/api/eventos", data={"sala_id": 1, "tipo": "x", "confianza": 0.5, "ocurrido_en": iso_utc(utcnow())})
    assert r.status_code == 401


def test_captura_que_no_es_imagen_se_rechaza(cliente):
    r = cliente.post(
        "/api/eventos",
        data={"sala_id": 1, "tipo": "x", "confianza": 0.5, "ocurrido_en": iso_utc(utcnow())},
        files={"captura": ("a.txt", b"no soy una imagen", "text/plain")},
        headers={"X-API-Key": API_KEY},
    )
    assert r.status_code == 422


# --- HU-02 -----------------------------------------------------------------
def test_hu02_filtros_por_sala_y_por_rango_de_fechas(cliente):
    disparar(cliente, sala_id=1)
    disparar(cliente, sala_id=2)
    iniciar_sesion(cliente, "jefe@prueba.local")
    assert len(cliente.get("/api/eventos").json()) == 2
    assert len(cliente.get("/api/eventos", params={"sala_id": 2}).json()) == 1
    hoy = (utcnow() - timedelta(hours=5)).date().isoformat()
    assert len(cliente.get("/api/eventos", params={"desde": hoy, "hasta": hoy}).json()) == 2
    assert cliente.get("/api/eventos", params={"desde": "2020-01-01", "hasta": "2020-01-31"}).json() == []


def test_hu02_el_historial_muestra_si_fue_confirmado_o_descartado(cliente):
    a = disparar(cliente).json()["id"]
    b = disparar(cliente).json()["id"]
    iniciar_sesion(cliente, "guardia@prueba.local")
    cliente.post(f"/api/eventos/{a}/confirmar")
    cliente.post(f"/api/eventos/{b}/descartar")
    estados = {e["id"]: e["estado"] for e in cliente.get("/api/eventos").json()}
    assert estados == {a: "confirmado", b: "descartado"}


# --- HU-04 -----------------------------------------------------------------
def test_hu04_confirmar_crea_ticket_y_equipo_queda_pendiente_de_reposicion(cliente, db):
    ev_id = disparar(cliente).json()["id"]
    equipo = db.scalars(select(Equipo).where(Equipo.sala_id == 1)).first()
    iniciar_sesion(cliente, "guardia@prueba.local")
    r = cliente.post(f"/api/eventos/{ev_id}/confirmar", json={"equipo_id": equipo.id})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["estado"] == "confirmado" and cuerpo["ticket"].startswith("SAUL-")
    db.expire_all()
    assert db.get(Equipo, equipo.id).estado == "pendiente_reposicion"


def test_hu04_no_se_puede_confirmar_dos_veces(cliente):
    ev_id = disparar(cliente).json()["id"]
    iniciar_sesion(cliente, "guardia@prueba.local")
    assert cliente.post(f"/api/eventos/{ev_id}/confirmar").status_code == 200
    assert cliente.post(f"/api/eventos/{ev_id}/confirmar").status_code == 409


def test_hu04_equipo_de_otra_sala_se_rechaza(cliente, db):
    ev_id = disparar(cliente, sala_id=1).json()["id"]
    otro = db.scalars(select(Equipo).where(Equipo.sala_id == 2)).first()
    iniciar_sesion(cliente, "guardia@prueba.local")
    r = cliente.post(f"/api/eventos/{ev_id}/confirmar", json={"equipo_id": otro.id})
    assert r.status_code == 422


# --- HU-05 -----------------------------------------------------------------
def test_hu05_cifras_por_sala_mes_y_costo_estimado(cliente):
    ids = [disparar(cliente, sala_id=s).json()["id"] for s in (1, 1, 2)]
    iniciar_sesion(cliente, "guardia@prueba.local")
    cliente.post(f"/api/eventos/{ids[0]}/confirmar")
    cliente.post(f"/api/eventos/{ids[1]}/confirmar")
    cliente.post(f"/api/eventos/{ids[2]}/descartar")
    iniciar_sesion(cliente, "activos@prueba.local")
    c = cliente.get("/api/reportes/cifras").json()
    assert c["hurtos_confirmados"] == 2 and c["falsas_alarmas"] == 1
    assert c["por_sala"] == [{"sala": "Sala de prueba A", "hurtos": 2}]
    assert c["costo_estimado_usd"] == 2 * c["costo_por_equipo_usd"]
    assert c["latencia"]["porcentaje_dentro_sla"] == 100.0


# --- HU-06 -----------------------------------------------------------------
def test_hu06_aviso_publico_de_equipo_con_caso_abierto(cliente, db):
    ev_id = disparar(cliente).json()["id"]
    equipo = db.scalars(select(Equipo).where(Equipo.sala_id == 1)).first()
    assert cliente.get(f"/api/publico/equipos/{equipo.numero_serie}").json()["con_falla_reportada"] is False
    iniciar_sesion(cliente, "guardia@prueba.local")
    cliente.post(f"/api/eventos/{ev_id}/confirmar", json={"equipo_id": equipo.id})
    cliente.cookies.clear()  # el estudiante no inicia sesión
    aviso = cliente.get(f"/api/publico/equipos/{equipo.numero_serie}").json()
    assert aviso["con_falla_reportada"] is True and aviso["ticket"].startswith("SAUL-")
    assert "id" not in aviso and "usuario" not in str(aviso).lower()


# --- Seguridad y privacidad -------------------------------------------------
def test_sin_sesion_no_se_puede_ver_el_historial(cliente):
    assert cliente.get("/api/eventos").status_code == 401


def test_login_con_clave_incorrecta_falla(cliente):
    r = cliente.post("/api/login", json={"correo": "guardia@prueba.local", "password": "incorrecta"})
    assert r.status_code == 401


def test_gestion_de_activos_ve_el_historial_pero_no_las_capturas(cliente):
    ev = disparar(cliente).json()
    iniciar_sesion(cliente, "activos@prueba.local")
    fila = cliente.get("/api/eventos").json()[0]
    assert fila["captura_url"] is None
    assert cliente.get(f"/api/eventos/{ev['id']}/captura").status_code == 403


def test_guardia_no_ve_las_cifras(cliente):
    iniciar_sesion(cliente, "guardia@prueba.local")
    assert cliente.get("/api/reportes/cifras").status_code == 403


def test_cada_consulta_queda_en_la_bitacora(cliente, db):
    ev = disparar(cliente).json()
    iniciar_sesion(cliente, "guardia@prueba.local")
    cliente.get("/api/eventos")
    cliente.get(f"/api/eventos/{ev['id']}/captura")
    acciones = [a.accion for a in db.scalars(select(Auditoria))]
    assert "consulta_historial" in acciones and "consulta_captura" in acciones
