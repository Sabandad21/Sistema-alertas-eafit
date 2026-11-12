"""Pruebas de las reglas con secuencias sintéticas de detecciones (2 cuadros por segundo)."""
from app.detection.rules import Deteccion, MotorReglas, ReglasConfig

T0 = 1_800_000_000.0  # un instante cualquiera (epoch)
PERSONA = Deteccion("person", 0.9, (100, 100, 220, 400))
PORTATIL = Deteccion("laptop", 0.85, (225, 250, 325, 320))  # junto a la persona
PORTATIL_LEJOS = Deteccion("laptop", 0.85, (900, 250, 1000, 320))


def correr(motor, segundos, detecciones, inicio=0.0, paso=0.5):
    eventos = []
    t = inicio
    while t < inicio + segundos:
        eventos += motor.procesar(T0 + t, detecciones)
        t += paso
    return eventos


def test_portatil_que_desaparece_con_persona_en_cuadro_genera_equipo_retirado():
    motor = MotorReglas(ReglasConfig(hora_fija=12))
    assert correr(motor, 6, [PORTATIL_LEJOS]) == []  # el portátil se ve estable
    eventos = correr(motor, 6, [PERSONA], inicio=6)  # desaparece, y hay una persona
    tipos = [e.tipo for e in eventos]
    assert tipos == ["equipo_retirado"]
    assert eventos[0].confianza >= 0.6


def test_portatil_que_desaparece_sin_persona_no_genera_evento():
    motor = MotorReglas(ReglasConfig(hora_fija=12))
    correr(motor, 6, [PORTATIL_LEJOS])
    assert correr(motor, 10, [], inicio=6) == []


def test_parpadeo_corto_del_detector_no_genera_evento():
    motor = MotorReglas(ReglasConfig(hora_fija=12))
    correr(motor, 6, [PORTATIL_LEJOS])
    assert correr(motor, 1, [PERSONA], inicio=6) == []  # 1 s sin portátil: menos que el umbral
    assert correr(motor, 6, [PERSONA, PORTATIL_LEJOS], inicio=7) == []


def test_permanencia_junto_al_equipo_genera_evento_solo_pasado_el_umbral():
    motor = MotorReglas(ReglasConfig(hora_fija=12, permanencia_seg=8))
    assert correr(motor, 7, [PERSONA, PORTATIL]) == []
    eventos = correr(motor, 3, [PERSONA, PORTATIL], inicio=7)
    assert [e.tipo for e in eventos] == ["permanencia_prolongada"]


def test_persona_lejos_del_equipo_no_cuenta_como_permanencia():
    motor = MotorReglas(ReglasConfig(hora_fija=12))
    assert correr(motor, 30, [PERSONA, PORTATIL_LEJOS]) == []


def test_persona_fuera_de_horario_genera_evento():
    motor = MotorReglas(ReglasConfig(hora_fija=23, fuera_horario_seg=5))
    eventos = correr(motor, 8, [PERSONA])
    assert [e.tipo for e in eventos] == ["presencia_fuera_de_horario"]


def test_persona_en_horario_normal_no_genera_evento():
    motor = MotorReglas(ReglasConfig(hora_fija=15))
    assert correr(motor, 30, [PERSONA]) == []


def test_el_mismo_evento_no_se_repite_durante_el_cooldown():
    motor = MotorReglas(ReglasConfig(hora_fija=23, fuera_horario_seg=5, cooldown_seg=60))
    eventos = correr(motor, 50, [PERSONA])
    assert len(eventos) == 1
    eventos = correr(motor, 30, [PERSONA], inicio=50)  # pasa el cooldown
    assert len(eventos) == 1


def test_detecciones_de_baja_confianza_se_ignoran():
    motor = MotorReglas(ReglasConfig(hora_fija=23))
    debil = Deteccion("person", 0.2, (100, 100, 220, 400))
    assert correr(motor, 30, [debil]) == []
