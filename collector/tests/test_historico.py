import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import historico


def test_agregar_punto_dedup_misma_hora():
    h = {}
    ahora = datetime.datetime(2026, 8, 11, 14, 5)
    historico.agregar_punto(h, "MSFT", ahora, 500.0)
    historico.agregar_punto(h, "MSFT", ahora.replace(minute=40), 501.0)
    assert len(h["MSFT"]) == 1
    assert h["MSFT"][0]["valor"] == 500.0


def test_agregar_punto_hora_distinta_agrega():
    h = {}
    ahora = datetime.datetime(2026, 8, 11, 14, 0)
    historico.agregar_punto(h, "MSFT", ahora, 500.0)
    historico.agregar_punto(h, "MSFT", ahora + datetime.timedelta(hours=1), 502.0)
    assert len(h["MSFT"]) == 2


def test_sembrar_convierte_backfill_a_ts():
    h = {}
    historico.sembrar(h, "MSFT", [{"fecha": "2021-08-11", "valor": 289.05}])
    assert h["MSFT"] == [{"ts": "2021-08-11T00:00:00", "valor": 289.05}]


def test_compactar_colapsa_puntos_viejos_a_uno_por_dia():
    ahora = datetime.datetime(2026, 8, 11, 12, 0)
    dia_viejo = ahora - datetime.timedelta(days=100)
    h = {
        "MSFT": [
            {"ts": dia_viejo.replace(hour=9).isoformat(), "valor": 100.0},
            {"ts": dia_viejo.replace(hour=15).isoformat(), "valor": 105.0},
        ]
    }
    historico.compactar(h, ahora)
    assert h["MSFT"] == [{"ts": dia_viejo.replace(hour=15).isoformat(), "valor": 105.0}]


def test_compactar_mantiene_resolucion_horaria_reciente():
    ahora = datetime.datetime(2026, 8, 11, 12, 0)
    hace_1_dia = ahora - datetime.timedelta(days=1)
    h = {
        "MSFT": [
            {"ts": hace_1_dia.replace(hour=9).isoformat(), "valor": 100.0},
            {"ts": hace_1_dia.replace(hour=15).isoformat(), "valor": 105.0},
        ]
    }
    historico.compactar(h, ahora)
    assert len(h["MSFT"]) == 2


def test_compactar_descarta_puntos_mas_viejos_que_dias_max():
    ahora = datetime.datetime(2026, 8, 11, 12, 0)
    viejisimo = ahora - datetime.timedelta(days=historico.DIAS_MAX + 10)
    h = {"MSFT": [{"ts": viejisimo.isoformat(), "valor": 1.0}]}
    historico.compactar(h, ahora)
    assert h["MSFT"] == []


def test_derivar_rangos_shape():
    ahora = datetime.datetime(2026, 8, 11, 12, 0)
    serie = [
        {"ts": "2026-08-10T09:00:00", "valor": 500.0},
        {"ts": "2026-08-10T14:00:00", "valor": 502.0},
        {"ts": "2026-08-11T09:00:00", "valor": 503.0},
    ]
    rangos = historico.derivar_rangos(serie, ahora)
    assert set(rangos.keys()) == {"1M", "6M", "YTD", "1A", "5A"}
    assert len(rangos["1M"]) == 3
    assert len(rangos["6M"]) == 2


def test_derivar_rangos_un_punto_por_dia_toma_el_ultimo():
    ahora = datetime.datetime(2026, 8, 11, 12, 0)
    serie = [
        {"ts": "2026-08-10T09:00:00", "valor": 500.0},
        {"ts": "2026-08-10T14:00:00", "valor": 502.0},
    ]
    rangos = historico.derivar_rangos(serie, ahora)
    assert rangos["6M"] == [{"fecha": "2026-08-10", "valor": 502.0}]
