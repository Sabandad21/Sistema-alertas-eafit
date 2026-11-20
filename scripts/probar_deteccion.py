"""Prueba el detector con una imagen y revisa si las reglas generan un evento.

Uso (desde la raíz del repositorio, con el modelo en models/yolov8n.onnx):
    python -m scripts.probar_deteccion RUTA_IMAGEN [--hora 2] [--salida deteccion.jpg]

Qué hace:
  1. Detecta personas y equipos en la imagen con YOLOv8n (ONNX) y dibuja las cajas.
  2. Repite esa detección durante 9 segundos simulados en el motor de reglas, con la hora
     indicada (por defecto las 2 a. m., fuera del horario de ocupación).
  3. Imprime las detecciones, el tiempo que tardó el modelo y los eventos que salieron.
"""
import argparse
import sys
import time

import cv2

from app.detection.detector import DetectorYolo, dibujar
from app.detection.rules import MotorReglas, ReglasConfig


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("imagen")
    ap.add_argument("--modelo", default=None, help="ruta del .onnx (por defecto models/yolov8n.onnx)")
    ap.add_argument("--hora", type=int, default=2, help="hora simulada (0 a 23) para la regla de horario")
    ap.add_argument("--segundos", type=int, default=9, help="segundos simulados que se repite la imagen")
    ap.add_argument("--salida", default="deteccion.jpg", help="imagen de salida con las cajas")
    args = ap.parse_args()

    cuadro = cv2.imread(args.imagen)
    if cuadro is None:
        print(f"No se pudo leer la imagen: {args.imagen}")
        return 1

    detector = DetectorYolo(args.modelo)
    t0 = time.perf_counter()
    detecciones = detector.detectar(cuadro)
    ms = (time.perf_counter() - t0) * 1000
    print(f"Detecciones: {len(detecciones)} (tiempo: {ms:.0f} ms)")
    for d in detecciones:
        print(f"  {d.clase:7s} confianza {d.confianza:.2f}")
    cv2.imwrite(args.salida, dibujar(cuadro, detecciones))
    print(f"Imagen con cajas guardada en {args.salida}")

    motor = MotorReglas(ReglasConfig(hora_fija=args.hora))
    inicio = 1_800_000_000.0
    eventos = []
    for i in range(args.segundos):
        eventos += motor.procesar(inicio + i, detecciones)
    print(f"Eventos con la hora simulada {args.hora}:00 y {args.segundos} s de imagen: {len(eventos)}")
    for e in eventos:
        print(f"  {e.tipo} (confianza {e.confianza:.2f}) a los {e.ts - inicio:.0f} s: {e.detalle}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
