"""Programa que lee un video (o una webcam), detecta con YOLOv8 y avisa al servicio cuando una regla se cumple.

Ejemplos:
  python -m app.detection.worker --fuente videos/demo.mp4 --sala-id 1 --api-url http://localhost:8000
  python -m app.detection.worker --fuente 0 --sala-id 1 --api-url https://mi-servicio.azurewebsites.net --tiempo-real

La clave del servicio se toma de la variable DETECTOR_API_KEY (no se pasa por línea de comandos).
"""
import argparse
import os
import sys
import time
from datetime import datetime, timezone

import cv2
import httpx

from .detector import DetectorYolo, dibujar
from .rules import MotorReglas, ReglasConfig


def enviar_evento(cliente: httpx.Client, url: str, clave: str, sala_id: int, evento, captura: bytes) -> dict | None:
    # ocurrido_en es el momento en que la regla se cumplió (hora real del detector).
    ocurrido = datetime.now(timezone.utc).isoformat()
    for intento in (1, 2):
        try:
            r = cliente.post(
                f"{url}/api/eventos",
                data={"sala_id": sala_id, "tipo": evento.tipo, "confianza": evento.confianza, "ocurrido_en": ocurrido},
                files={"captura": ("captura.jpg", captura, "image/jpeg")},
                headers={"X-API-Key": clave},
                timeout=10.0,
            )
            if r.status_code == 201:
                return r.json()
            print(f"  El servicio respondió {r.status_code}: {r.text[:200]}", file=sys.stderr)
            return None
        except httpx.HTTPError as error:
            print(f"  Intento {intento}: no se pudo contactar al servicio ({error})", file=sys.stderr)
            time.sleep(1)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fuente", required=True, help="ruta de un video o índice de la cámara (0, 1...)")
    ap.add_argument("--sala-id", type=int, required=True)
    ap.add_argument("--api-url", default=os.getenv("API_URL", "http://localhost:8000"))
    ap.add_argument("--modelo", default=None, help="ruta del .onnx (por defecto models/yolov8n.onnx)")
    ap.add_argument("--fps-analisis", type=float, default=4.0, help="cuadros por segundo que se analizan")
    ap.add_argument("--tiempo-real", action="store_true", help="en un video, esperar para simular la velocidad real")
    ap.add_argument("--hora-simulada", type=int, default=None, help="hora (0-23) para probar la regla de fuera de horario")
    ap.add_argument("--confianza", type=float, default=0.40)
    args = ap.parse_args()

    clave = os.getenv("DETECTOR_API_KEY", "")
    if not clave:
        print("Falta la variable de entorno DETECTOR_API_KEY.", file=sys.stderr)
        return 2

    fuente = int(args.fuente) if args.fuente.isdigit() else args.fuente
    captura = cv2.VideoCapture(fuente)
    if not captura.isOpened():
        print(f"No se pudo abrir la fuente: {args.fuente}", file=sys.stderr)
        return 2
    es_camara = isinstance(fuente, int)
    fps_fuente = captura.get(cv2.CAP_PROP_FPS) or 25.0
    salto = max(1, round(fps_fuente / args.fps_analisis))

    detector = DetectorYolo(args.modelo, confianza_minima=min(args.confianza, 0.30))
    motor = MotorReglas(ReglasConfig(min_confianza=args.confianza, hora_fija=args.hora_simulada))

    inicio_real = time.time()
    n_cuadro, analizados, ms_total = 0, 0, 0.0
    enviados: list[dict] = []
    print(f"Analizando {args.fuente} (1 de cada {salto} cuadros, ~{fps_fuente / salto:.1f} cuadros/s)…")

    with httpx.Client() as cliente:
        while True:
            ok, cuadro = captura.read()
            if not ok:
                break
            n_cuadro += 1
            if n_cuadro % salto:
                continue
            # tiempo del cuadro: el reloj en una cámara; la posición dentro del video en un archivo
            t_video = (time.time() - inicio_real) if es_camara else n_cuadro / fps_fuente
            if args.tiempo_real and not es_camara:
                espera = t_video - (time.time() - inicio_real)
                if espera > 0:
                    time.sleep(espera)

            t0 = time.perf_counter()
            detecciones = detector.detectar(cuadro)
            ms_total += (time.perf_counter() - t0) * 1000
            analizados += 1

            for ev in motor.procesar(inicio_real + t_video, detecciones):
                print(f"[{t_video:6.1f} s] {ev.tipo} (confianza {ev.confianza:.0%}) – {ev.detalle}")
                ok_jpg, jpg = cv2.imencode(".jpg", dibujar(cuadro, detecciones), [cv2.IMWRITE_JPEG_QUALITY, 80])
                respuesta = enviar_evento(cliente, args.api_url, clave, args.sala_id, ev, jpg.tobytes())
                if respuesta:
                    enviados.append(respuesta)
                    print(f"           → evento {respuesta['id']} registrado; aviso en {respuesta['latencia_seg']} s")

    captura.release()
    print("\nResumen")
    print(f"  Cuadros analizados: {analizados}; inferencia promedio: {ms_total / max(analizados, 1):.0f} ms por cuadro")
    print(f"  Eventos enviados: {len(enviados)}")
    if enviados:
        lat = [e["latencia_seg"] for e in enviados if e["latencia_seg"] is not None]
        print(f"  Tiempo hasta el aviso: máx. {max(lat)} s (criterio: menos de 30 s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
