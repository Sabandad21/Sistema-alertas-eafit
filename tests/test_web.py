"""Pruebas de las páginas web: acceso por rol, login con formulario y cabeceras de seguridad."""
from .conftest import PASSWORD


def test_sin_sesion_las_paginas_redirigen_al_login(cliente):
    for ruta in ("/alertas", "/historial", "/panel", "/equipos", "/evento/1"):
        r = cliente.get(ruta, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/login", ruta


def test_login_con_formulario_redirige_segun_el_rol(cliente):
    r = cliente.post("/login", data={"correo": "guardia@prueba.local", "password": PASSWORD}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/alertas"
    cliente.cookies.clear()
    r = cliente.post("/login", data={"correo": "activos@prueba.local", "password": PASSWORD}, follow_redirects=False)
    assert r.headers["location"] == "/panel"


def test_login_incorrecto_muestra_error_sin_abrir_sesion(cliente):
    r = cliente.post("/login", data={"correo": "guardia@prueba.local", "password": "mala"}, follow_redirects=False)
    assert r.status_code == 200 and "incorrectos" in r.text
    assert cliente.get("/alertas", follow_redirects=False).status_code == 303


def test_gestion_de_activos_no_entra_a_las_alertas(cliente):
    cliente.post("/login", data={"correo": "activos@prueba.local", "password": PASSWORD})
    r = cliente.get("/alertas", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/historial"
    assert cliente.get("/panel").status_code == 200


def test_la_pagina_del_qr_es_publica(cliente):
    r = cliente.get("/aviso/TEST-A-001")
    assert r.status_code == 200 and "TEST-A-001" in r.text


def test_cabeceras_de_seguridad_presentes(cliente):
    r = cliente.get("/login")
    assert "default-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"


def test_la_cookie_de_sesion_no_es_accesible_desde_javascript(cliente):
    r = cliente.post("/api/login", json={"correo": "guardia@prueba.local", "password": PASSWORD})
    assert "httponly" in r.headers["set-cookie"].lower()


def test_salud(cliente):
    assert cliente.get("/salud").json() == {"estado": "ok"}
