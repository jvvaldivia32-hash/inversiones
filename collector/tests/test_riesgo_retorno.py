import datetime
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import riesgo_retorno as rr

AHORA = datetime.datetime(2026, 9, 30, 15, 0, tzinfo=datetime.timezone.utc)


def _serie(dias: int, precio_fn, incluir_findes: bool = True) -> list[dict]:
    hoy = AHORA.date()
    salida = []
    for i in range(dias, -1, -1):
        d = hoy - datetime.timedelta(days=i)
        if not incluir_findes and d.weekday() >= 5:
            continue
        salida.append({"ts": f"{d.isoformat()}T20:00:00", "valor": precio_fn(dias - i)})
    return salida


def test_retorno_anual_es_geometrico():
    # Duplica en 5 años exactos → 14,87% anual, no 20% (que sería el promedio simple).
    dias = round(365.25 * 5)
    serie = _serie(dias, lambda i: 100 * 2 ** (i / dias))
    r = rr.calcular(serie, AHORA)
    assert abs(r["retorno_anual_pct"]["5A"] - (2 ** (1 / 5) - 1) * 100) < 0.2


def test_sin_historia_suficiente_no_inventa_horizontes_largos():
    r = rr.calcular(_serie(400, lambda i: 100 + i), AHORA)
    assert "1A" in r["retorno_anual_pct"]
    assert "3A" not in r["retorno_anual_pct"]
    assert "10A" not in r["retorno_anual_pct"]


def test_findes_repetidos_no_bajan_la_volatilidad():
    # El recolector guarda el cierre del viernes también el sábado y el domingo. Con esos
    # "días" de 0% la volatilidad saldría ~17% más baja: tienen que filtrarse.
    def precio(i):
        return 100 * math.exp(0.01 * (1 if i % 2 else -1))

    con_findes = rr.calcular(_serie(400, precio, incluir_findes=True), AHORA)
    sin_findes = rr.calcular(_serie(400, precio, incluir_findes=False), AHORA)
    assert abs(con_findes["volatilidad_anual_pct"] - sin_findes["volatilidad_anual_pct"]) < 0.5


def test_caida_maxima_desde_el_maximo_previo():
    precios = [100, 120, 90, 110, 60, 130]
    hoy = AHORA.date()
    serie = []
    d = hoy - datetime.timedelta(days=40)
    for p in precios:
        while d.weekday() >= 5:
            d += datetime.timedelta(days=1)
        serie.append({"ts": f"{d.isoformat()}T20:00:00", "valor": p})
        d += datetime.timedelta(days=1)
    r = rr.calcular(serie, AHORA)
    assert round(r["caida_maxima_5a_pct"], 1) == -50.0  # 120 → 60


def test_historia_corta_no_da_volatilidad():
    r = rr.calcular(_serie(60, lambda i: 100 + i), AHORA)
    assert "volatilidad_anual_pct" not in r


def test_sin_datos_devuelve_none():
    assert rr.calcular([], AHORA) is None
