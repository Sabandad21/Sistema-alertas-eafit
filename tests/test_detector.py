"""Prueba del procesamiento del detector con una salida de modelo simulada (no necesita el archivo .onnx)."""
import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("cv2")

from app.detection.detector import TAMANO, DetectorYolo, dibujar  # noqa: E402


class SesionFalsa:
    """Imita onnxruntime: devuelve un tensor (1, 84, 8400) con una persona y un portátil."""

    def __init__(self):
        self.recibido = None

    def get_inputs(self):
        class Entrada:
            name = "images"

        return [Entrada()]

    def run(self, _, entradas):
        self.recibido = entradas["images"]
        salida = np.zeros((1, 84, 8400), dtype=np.float32)
        # ancla 0: persona (clase 0) en cx=320, cy=320, w=100, h=200 (coordenadas del cuadro de 640x640)
        salida[0, :4, 0] = [320, 320, 100, 200]
        salida[0, 4 + 0, 0] = 0.90
        # ancla 1: portátil (clase 63)
        salida[0, :4, 1] = [100, 500, 80, 60]
        salida[0, 4 + 63, 1] = 0.75
        # ancla 2: un objeto que no interesa (clase 2, "car") no debe salir
        salida[0, :4, 2] = [500, 100, 80, 60]
        salida[0, 4 + 2, 2] = 0.95
        return [salida]


def _detector():
    d = DetectorYolo.__new__(DetectorYolo)
    d.sesion = SesionFalsa()
    d.entrada = "images"
    d.confianza_minima = 0.30
    d.iou_nms = 0.45
    return d


def test_el_cuadro_se_prepara_a_640_y_las_cajas_vuelven_a_coordenadas_originales():
    d = _detector()
    cuadro = np.zeros((720, 1280, 3), dtype=np.uint8)  # 16:9: escala 0.5, relleno vertical de 140 px
    dets = d.detectar(cuadro)

    assert d.sesion.recibido.shape == (1, 3, TAMANO, TAMANO)
    por_clase = {x.clase: x for x in dets}
    assert set(por_clase) == {"person", "laptop"}  # "car" se ignora
    x1, y1, x2, y2 = por_clase["person"].caja
    assert (x1, y1, x2, y2) == pytest.approx((540, 160, 740, 560), abs=2)
    assert por_clase["person"].confianza == pytest.approx(0.90, abs=1e-3)


def test_dibujar_no_modifica_el_cuadro_original():
    d = _detector()
    cuadro = np.zeros((720, 1280, 3), dtype=np.uint8)
    dets = d.detectar(cuadro)
    con_cajas = dibujar(cuadro, dets)
    assert cuadro.sum() == 0 and con_cajas.sum() > 0
