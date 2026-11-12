"""Descarga YOLOv8n (preentrenado en COCO) y lo exporta a models/yolov8n.onnx.

Uso:  pip install -r requirements-dev.txt  &&  python -m scripts.exportar_modelo
Solo se necesita una vez; el archivo .onnx ya viene en el repositorio.
"""
import os
import shutil

from ultralytics import YOLO


def main() -> None:
    modelo = YOLO("yolov8n.pt")  # se descarga automáticamente
    ruta = modelo.export(format="onnx", imgsz=640, opset=12, simplify=False)
    os.makedirs("models", exist_ok=True)
    shutil.move(ruta, os.path.join("models", "yolov8n.onnx"))
    print("Modelo guardado en models/yolov8n.onnx")


if __name__ == "__main__":
    main()
