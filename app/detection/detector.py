"""Detector de objetos YOLOv8 en formato ONNX (se ejecuta con onnxruntime, sin PyTorch).

El modelo es YOLOv8n preentrenado en COCO. Solo se conservan las clases que usan las reglas.
Para generar el archivo .onnx ver scripts/exportar_modelo.py.
"""
import os

import cv2
import numpy as np

from .rules import Deteccion

# Nombres de las 80 clases COCO en el orden del modelo; solo se usan las de interés.
CLASES_COCO = {0: "person", 62: "tv", 63: "laptop", 64: "mouse", 66: "keyboard"}
TAMANO = 640


class DetectorYolo:
    def __init__(self, ruta_modelo: str | None = None, confianza_minima: float = 0.30, iou_nms: float = 0.45):
        import onnxruntime as ort

        ruta = ruta_modelo or os.getenv("MODELO_ONNX", "models/yolov8n.onnx")
        if not os.path.isfile(ruta):
            raise FileNotFoundError(f"No se encontró el modelo en {ruta}. Ejecute: python -m scripts.exportar_modelo")
        self.sesion = ort.InferenceSession(ruta, providers=["CPUExecutionProvider"])
        self.entrada = self.sesion.get_inputs()[0].name
        self.confianza_minima = confianza_minima
        self.iou_nms = iou_nms

    @staticmethod
    def _preparar(cuadro: np.ndarray):
        """Redimensiona a 640x640 conservando la proporción (rellena con gris). Devuelve tensor, escala y relleno."""
        alto, ancho = cuadro.shape[:2]
        escala = min(TAMANO / alto, TAMANO / ancho)
        nuevo_ancho, nuevo_alto = int(round(ancho * escala)), int(round(alto * escala))
        redim = cv2.resize(cuadro, (nuevo_ancho, nuevo_alto), interpolation=cv2.INTER_LINEAR)
        lienzo = np.full((TAMANO, TAMANO, 3), 114, dtype=np.uint8)
        dx, dy = (TAMANO - nuevo_ancho) // 2, (TAMANO - nuevo_alto) // 2
        lienzo[dy : dy + nuevo_alto, dx : dx + nuevo_ancho] = redim
        tensor = lienzo[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0  # BGR->RGB, NCHW
        return np.ascontiguousarray(tensor), escala, dx, dy

    def detectar(self, cuadro: np.ndarray) -> list[Deteccion]:
        tensor, escala, dx, dy = self._preparar(cuadro)
        salida = self.sesion.run(None, {self.entrada: tensor})[0][0]  # (84, 8400)
        filas = salida.T  # (8400, 84): cx, cy, w, h, 80 puntajes de clase
        puntajes = filas[:, 4:]
        ids = puntajes.argmax(axis=1)
        conf = puntajes.max(axis=1)
        # Solo las clases de interés y con confianza suficiente
        mascara = np.isin(ids, list(CLASES_COCO)) & (conf >= self.confianza_minima)
        if not mascara.any():
            return []
        filas, ids, conf = filas[mascara], ids[mascara], conf[mascara]
        cajas = []
        for cx, cy, w, h in filas[:, :4]:
            cajas.append([int(cx - w / 2), int(cy - h / 2), int(w), int(h)])
        indices = cv2.dnn.NMSBoxes(cajas, conf.tolist(), self.confianza_minima, self.iou_nms)
        resultado = []
        alto, ancho = cuadro.shape[:2]
        for i in np.array(indices).flatten():
            x, y, w, h = cajas[i]
            x1 = max(0.0, (x - dx) / escala)
            y1 = max(0.0, (y - dy) / escala)
            x2 = min(float(ancho), (x + w - dx) / escala)
            y2 = min(float(alto), (y + h - dy) / escala)
            resultado.append(Deteccion(CLASES_COCO[int(ids[i])], float(conf[i]), (x1, y1, x2, y2)))
        return resultado


def dibujar(cuadro: np.ndarray, detecciones: list[Deteccion]) -> np.ndarray:
    """Copia del cuadro con las cajas dibujadas, para la captura que acompaña la alerta."""
    salida = cuadro.copy()
    for d in detecciones:
        x1, y1, x2, y2 = (int(v) for v in d.caja)
        color = (0, 0, 220) if d.clase == "person" else (0, 160, 0)
        cv2.rectangle(salida, (x1, y1), (x2, y2), color, 2)
        cv2.putText(salida, f"{d.clase} {d.confianza:.0%}", (x1, max(14, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return salida
