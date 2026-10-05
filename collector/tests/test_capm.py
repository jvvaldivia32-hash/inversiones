import datetime
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import capm

AHORA = datetime.datetime(2026, 10, 5, 16, 0)


def _serie(retornos: list[float], inicio=datetime.date(2025, 9, 25), precio=100.0) -> list[dict]:
    """Un punto por día hábil a partir de `inicio`, aplicando cada retorno en orden."""
    puntos, dia = [], inicio
    for r in [0.0] + retornos:
        while dia.weekday() >= 5:
            dia += datetime.timedelta(days=1)
        precio *= 1 + r
        puntos.append({"ts": f"{dia.isoformat()}T00:00:00", "valor": precio})
        dia += datetime.timedelta(days=1)
    return puntos


def _mercado(n=270, semilla=1):
    rnd = random.Random(semilla)
    return [rnd.gauss(0.0005, 0.01) for _ in range(n)]


def test_beta_de_un_ticker_que_duplica_al_mercado():
    m = _mercado()
    hist = {"VOO": _serie(m), "X": _serie([2 * r for r in m])}
    res = capm.calcular(hist, ["X"], 4.0, "2025-10-03", AHORA)
    x = res["por_ticker"]["X"]
    assert x["beta"] == pytest.approx(2.0, abs=0.01)
    # esperado = Rf + β (Rm − Rf), con Rm medido entre las mismas fechas que X
    assert x["esperado_capm_pct"] == pytest.approx(4.0 + x["beta"] * (x["mercado_1a_pct"] - 4.0), abs=0.02)
    assert x["diferencia_pts"] == pytest.approx(x["retorno_1a_pct"] - x["esperado_capm_pct"], abs=0.02)


def test_el_mercado_contra_si_mismo_no_tiene_diferencia():
    hist = {"VOO": _serie(_mercado())}
    v = capm.calcular(hist, ["VOO"], 4.0, "2025-10-03", AHORA)["por_ticker"]["VOO"]
    assert v["beta"] == pytest.approx(1.0)
    assert v["diferencia_pts"] == pytest.approx(0.0, abs=0.01)


def test_sin_un_anio_de_historia_no_se_inventa():
    m = _mercado()
    hist = {"VOO": _serie(m), "NUEVO": _serie(m[:60], inicio=datetime.date(2026, 7, 1))}
    res = capm.calcular(hist, ["NUEVO", "VOO"], 4.0, "2025-10-03", AHORA)
    assert "NUEVO" not in res["por_ticker"]


def test_hueco_largo_no_cuenta_como_retorno_de_un_dia():
    m = _mercado()
    serie = _serie(m)
    # seis semanas sin datos con un salto de +30%: no debe entrar a la beta
    sin_hueco = [p for p in serie if not ("2026-06-01" <= p["ts"][:10] <= "2026-07-12")]
    for p in sin_hueco:
        if p["ts"][:10] > "2026-07-12":
            p["valor"] *= 1.3
    hist = {"VOO": serie, "X": sin_hueco}
    x = capm.calcular(hist, ["X"], 4.0, "2025-10-03", AHORA)["por_ticker"]["X"]
    assert x["beta"] == pytest.approx(1.0, abs=0.01)


def test_matriz_de_correlaciones_simetrica_con_diagonal_1():
    m = _mercado()
    rnd = random.Random(7)
    hist = {"VOO": _serie(m), "A": _serie([r + rnd.gauss(0, 0.01) for r in m]), "B": _serie([-r for r in m])}
    corr = capm.calcular(hist, ["A", "B", "VOO"], 4.0, "2025-10-03", AHORA)["correlaciones"]
    i = {t: n for n, t in enumerate(corr["tickers"])}
    mat = corr["matriz"]
    assert all(mat[k][k] == 1.0 for k in range(len(mat)))
    assert mat[i["A"]][i["B"]] == mat[i["B"]][i["A"]]
    assert mat[i["B"]][i["VOO"]] == pytest.approx(-1.0, abs=0.001)


def test_sin_mercado_devuelve_none():
    assert capm.calcular({"X": _serie(_mercado())}, ["X"], 4.0, "2025-10-03", AHORA) is None
