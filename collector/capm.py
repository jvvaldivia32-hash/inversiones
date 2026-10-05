"""CAPM ex post del último año, por ticker, más lo que hace falta para analizar una cartera
(pedido de José 2026-10-05: "ver si está rentando más o menos que su CAPM").

Para cada ticker, sobre la misma ventana de un año:

- **Retorno**: precio final / precio inicial − 1 (solo precio, sin dividendos — igual que
  riesgo_retorno.py).
- **Beta**: covarianza de los retornos diarios del ticker con los de VOO (el S&P 500) sobre
  la varianza de VOO.
- **Lo que esperaba el CAPM**: Rf + β · (Rm − Rf), con Rf = bono del Tesoro de EE.UU. a 1
  año al inicio de la ventana (sources/tesoro.py) y Rm = retorno de VOO entre las mismas
  dos fechas que el ticker.
- **Diferencia**: retorno − esperado (el "alfa de Jensen"). Es un dato del pasado, no un
  veredicto: la vista nunca lo traduce a "compra"/"vende" (regla dura del Radar).

Para la cartera (que se arma en el navegador, porque "Mi inversión" vive en un repo privado
que el recolector no puede leer — excepción #3) se publica la volatilidad de cada ticker y
la matriz de correlaciones: con eso el navegador saca σ de cualquier combinación de pesos.

Los retornos diarios saltan los huecos de más de 4 días corridos (un viernes→lunes son 3):
los tickers del universo del Radar tuvieron un hueco de seis semanas en el historial
(agosto–octubre 2026, Finnhub respondiendo 429) y ese "retorno de seis semanas" metido como
si fuera de un día ensuciaría la beta.
"""

import datetime
import math
import statistics

from riesgo_retorno import _cierres_por_dia

MERCADO = "VOO"
DIAS_HABILES_POR_ANIO = 252
TOLERANCIA_DIAS = 15  # mismo margen que riesgo_retorno.py para el punto inicial
MAX_HUECO_DIAS = 4
MINIMO_RETORNOS = 150  # ~7 meses hábiles; con menos, beta/correlación no son serias


def _retornos_diarios(cierres: list[tuple[datetime.date, float]]) -> dict[datetime.date, float]:
    salida = {}
    for (d0, v0), (d1, v1) in zip(cierres, cierres[1:]):
        if (d1 - d0).days <= MAX_HUECO_DIAS and v0 > 0:
            salida[d1] = v1 / v0 - 1
    return salida


def _precio_en_o_despues(cierres, fecha):
    return next(((d, v) for d, v in cierres if d >= fecha), None)


def _precio_en_o_antes(cierres, fecha):
    previos = [(d, v) for d, v in cierres if d <= fecha]
    return previos[-1] if previos else None


def _cov_corr(a: dict, b: dict) -> tuple[float, float, float] | None:
    """(cov, var_a, var_b) sobre los días en común, o None si son muy pocos."""
    dias = sorted(set(a) & set(b))
    if len(dias) < MINIMO_RETORNOS:
        return None
    xa = [a[d] for d in dias]
    xb = [b[d] for d in dias]
    return statistics.covariance(xa, xb), statistics.variance(xa), statistics.variance(xb)


def calcular(
    hist: dict, tickers: list[str], rf_pct: float, rf_fecha: str, ahora: datetime.datetime
) -> dict | None:
    hoy = ahora.date()
    desde = hoy - datetime.timedelta(days=365)

    cierres_mercado = [(d, v) for d, v in _cierres_por_dia(hist.get(MERCADO, [])) if d >= desde - datetime.timedelta(days=TOLERANCIA_DIAS)]
    ret_mercado = {d: r for d, r in _retornos_diarios(cierres_mercado).items() if d > desde}
    if len(ret_mercado) < MINIMO_RETORNOS:
        return None

    por_ticker: dict[str, dict] = {}
    retornos: dict[str, dict] = {}
    for ticker in dict.fromkeys(tickers):
        cierres = [(d, v) for d, v in _cierres_por_dia(hist.get(ticker, [])) if d >= desde]
        if len(cierres) < 2 or (cierres[0][0] - desde).days > TOLERANCIA_DIAS:
            continue  # sin un año de historia no se inventa un retorno anual
        (d_ini, p_ini), (d_fin, p_fin) = cierres[0], cierres[-1]
        m_ini = _precio_en_o_despues(cierres_mercado, d_ini)
        m_fin = _precio_en_o_antes(cierres_mercado, d_fin)
        if not m_ini or not m_fin or m_ini[0] >= m_fin[0]:
            continue

        r = _retornos_diarios(cierres)
        stats = _cov_corr(r, ret_mercado)
        if stats is None:
            continue
        cov, var_t, var_m = stats
        beta = cov / var_m
        retorno = (p_fin / p_ini - 1) * 100
        retorno_mercado = (m_fin[1] / m_ini[1] - 1) * 100
        esperado = rf_pct + beta * (retorno_mercado - rf_pct)
        retornos[ticker] = r
        por_ticker[ticker] = {
            "beta": round(beta, 2),
            "retorno_1a_pct": round(retorno, 2),
            "mercado_1a_pct": round(retorno_mercado, 2),
            "esperado_capm_pct": round(esperado, 2),
            "diferencia_pts": round(retorno - esperado, 2),
            "volatilidad_pct": round(math.sqrt(statistics.variance(r.values()) * DIAS_HABILES_POR_ANIO) * 100, 2),
            "desde": d_ini.isoformat(),
            "hasta": d_fin.isoformat(),
        }

    if not por_ticker:
        return None

    orden = sorted(por_ticker)
    matriz = []
    for a in orden:
        fila = []
        for b in orden:
            if a == b:
                fila.append(1.0)
                continue
            stats = _cov_corr(retornos[a], retornos[b])
            fila.append(round(stats[0] / math.sqrt(stats[1] * stats[2]), 3) if stats and stats[1] and stats[2] else None)
        matriz.append(fila)

    return {
        "rf_pct": rf_pct,
        "rf_fecha": rf_fecha,
        "mercado": MERCADO,
        "por_ticker": por_ticker,
        "correlaciones": {"tickers": orden, "matriz": matriz},
    }
