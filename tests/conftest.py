import os
import tempfile

# La configuración se lee al importar la app, así que se define antes.
_carpeta = tempfile.mkdtemp(prefix="alertas_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_carpeta}/test.db"
os.environ["CAPTURAS_DIR"] = f"{_carpeta}/capturas"
os.environ["SECRET_KEY"] = "clave-solo-para-pruebas"
os.environ["DETECTOR_API_KEY"] = "api-key-solo-para-pruebas"
os.environ["TEAMS_WEBHOOK_URL"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import sembrar  # noqa: E402

PASSWORD = "Prueba-123"
API_KEY = os.environ["DETECTOR_API_KEY"]


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as sesion:
        sembrar(sesion, PASSWORD)
        yield sesion


@pytest.fixture()
def cliente(db):
    with TestClient(app) as c:
        yield c


def iniciar_sesion(cliente, correo: str) -> None:
    r = cliente.post("/api/login", json={"correo": correo, "password": PASSWORD})
    assert r.status_code == 200, r.text
