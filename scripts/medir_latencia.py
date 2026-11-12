"""Mide el criterio de aceptación de la HU-01: aviso en menos de 30 segundos.

Envía N eventos de prueba al servicio (como lo haría el detector) y reporta, para cada uno, el tiempo entre que
el detector dispara la regla y el sistema envía el aviso. Guarda el detalle en un CSV como evidencia.

Uso:
  DETECTOR_API_KEY=... python -m scripts.medir_latencia --api-url https://mi-servicio --sala-id 1 --n 30

Los eventos quedan como "pendientes" de tipo "simulado": descártelos desde la pantalla de alertas después de medir.
Si el detector y el servidor están en máquinas distintas, sus relojes deben estar sincronizados (NTP).
"""
import argparse
import csv
import os
import statistics
import sys
import time
from datetime import datetime, timezone

import httpx

# JPEG mínimo válido (1x1) para acompañar el evento
JPEG_1X1 = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501010101010100000000000000000102030405060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda0008010100003f00fbfcffd9"
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api-url", default=os.getenv("API_URL", "http://localhost:8000"))
    ap.add_argument("--sala-id", type=int, default=1)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--salida", default="resultados_latencia.csv")
    args = ap.parse_args()

    clave = os.getenv("DETECTOR_API_KEY", "")
    if not clave:
        print("Falta la variable de entorno DETECTOR_API_KEY.", file=sys.stderr)
        return 2

    filas = []
    with httpx.Client(timeout=15.0) as cliente:
        for i in range(1, args.n + 1):
            ocurrido = datetime.now(timezone.utc)
            t0 = time.perf_counter()
            r = cliente.post(
                f"{args.api_url}/api/eventos",
                data={"sala_id": args.sala_id, "tipo": "simulado", "confianza": 0.9, "ocurrido_en": ocurrido.isoformat()},
                files={"captura": ("c.jpg", JPEG_1X1, "image/jpeg")},
                headers={"X-API-Key": clave},
            )
            ida_y_vuelta = time.perf_counter() - t0
            if r.status_code != 201:
                print(f"Evento {i}: el servicio respondió {r.status_code}: {r.text[:150]}", file=sys.stderr)
                continue
            datos = r.json()
            filas.append({"n": i, "evento_id": datos["id"], "ocurrido_en": ocurrido.isoformat(), "latencia_servidor_s": datos["latencia_seg"], "ida_y_vuelta_s": round(ida_y_vuelta, 3)})
            time.sleep(0.2)

    if not filas:
        print("No se registró ningún evento.", file=sys.stderr)
        return 1
    with open(args.salida, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)

    lat = sorted(x["latencia_servidor_s"] for x in filas)
    p95 = lat[min(len(lat) - 1, int(round(0.95 * (len(lat) - 1))))]
    dentro = sum(1 for x in lat if x <= 30)
    print(f"Eventos medidos: {len(lat)}")
    print(f"Tiempo hasta el aviso: mínimo {lat[0]} s · promedio {statistics.mean(lat):.2f} s · p95 {p95} s · máximo {lat[-1]} s")
    print(f"Dentro de 30 s: {dentro}/{len(lat)} ({100 * dentro / len(lat):.0f} %)  → {'CUMPLE' if dentro == len(lat) else 'NO CUMPLE'}")
    print(f"Detalle guardado en {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
