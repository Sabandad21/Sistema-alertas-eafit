"""Crea datos de prueba. Uso:  python -m scripts.seed [--historial]

La contraseña de los usuarios de prueba se toma de SEED_PASSWORD; si no existe, se genera una y se imprime.
"""
import argparse
import os
import secrets

from app.db import Base, SessionLocal, engine
from app.seed import USUARIOS, sembrar


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historial", action="store_true", help="agrega ~35 eventos de los últimos 6 meses")
    args = parser.parse_args()

    Base.metadata.create_all(engine)
    password = os.getenv("SEED_PASSWORD") or secrets.token_urlsafe(9)
    with SessionLocal() as db:
        if sembrar(db, password, historial=args.historial):
            print("Datos de prueba creados. Usuarios:")
            for _, correo, rol in USUARIOS:
                print(f"  {correo}  ({rol})")
            print(f"Contraseña: {password}")
        else:
            print("La base ya tiene datos; no se cambió nada.")


if __name__ == "__main__":
    main()
