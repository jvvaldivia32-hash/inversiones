"""Métricas avanzadas por posición (Market Cap, EV, ROE/ROIC/ROCE, múltiplos, beta) —
extra fuera del plan madre, pedido por el usuario 2026-08-14. Cada campo se calcula
independiente y degrada a None si falta un insumo — nunca inventa un valor a partir de
datos parciales, mismo criterio que radar.evaluar_sana()."""

import datetime
import statistics

import radar

TRIMESTRES_TTM = 4
MINIMO_PUNTOS_BETA = 60  # ~3 meses de trading — menos que eso, el beta es puro ruido


def _ttm(serie: list[dict] | None) -> float | None:
    """Suma de los últimos 4 trimestres (trailing twelve months) — None si la serie no
    tiene ni 4 puntos, en vez de sumar un TTM parcial que se vería completo pero no lo
    es."""
    if not serie or len(serie) < TRIMESTRES_TTM:
        return None
    return sum(p["valor"] for p in serie[-TRIMESTRES_TTM:])


def calcular_beta(serie_ticker: list[dict], serie_mercado: list[dict]) -> float | None:
    """Beta propio contra el histórico de VOO ya guardado (no es el beta "oficial" de un
    proveedor pago — es una regresión real sobre datos reales, con las limitaciones de
    cualquier beta calculado sobre una sola serie de precios). None si hay menos de
    MINIMO_PUNTOS_BETA retornos diarios en común (ticker recién sembrado, por ejemplo)."""
    por_dia_ticker = {p["ts"][:10]: p["valor"] for p in serie_ticker}
    por_dia_mercado = {p["ts"][:10]: p["valor"] for p in serie_mercado}
    dias_comunes = sorted(set(por_dia_ticker) & set(por_dia_mercado))
    if len(dias_comunes) < MINIMO_PUNTOS_BETA + 1:
        return None

    retornos_ticker = []
    retornos_mercado = []
    for dia_anterior, dia_actual in zip(dias_comunes, dias_comunes[1:]):
        v_ant_t, v_act_t = por_dia_ticker[dia_anterior], por_dia_ticker[dia_actual]
        v_ant_m, v_act_m = por_dia_mercado[dia_anterior], por_dia_mercado[dia_actual]
        if v_ant_t and v_ant_m:
            retornos_ticker.append((v_act_t - v_ant_t) / v_ant_t)
            retornos_mercado.append((v_act_m - v_ant_m) / v_ant_m)

    if len(retornos_mercado) < MINIMO_PUNTOS_BETA:
        return None

    varianza_mercado = statistics.variance(retornos_mercado)
    if varianza_mercado == 0:
        return None
    return statistics.covariance(retornos_ticker, retornos_mercado) / varianza_mercado


def calcular_metricas(
    ticker: str,
    fundamentales: dict | None,
    balance: dict | None,
    precio: float,
    hist_ticker: list[dict],
    hist_mercado: list[dict],
    ahora: datetime.datetime,
) -> dict | None:
    """Combina fundamentales (EDGAR, MUSD), balance (EDGAR, USD crudo) y precio en las
    métricas de la sección "avanzada". None si no hay ni fundamentales ni balance — un
    ticker sin CIK (ej. VOO) no debería llegar hasta acá, pero si llega, no hay nada real
    que calcular."""
    if fundamentales is None and balance is None:
        return None

    series = (fundamentales or {}).get("series", {})
    balance = balance or {}

    ingresos_ttm = _ttm(series.get("ingresos_musd"))
    op_income_ttm = _ttm(series.get("op_income_musd"))
    utilidad_neta_ttm = _ttm(series.get("utilidad_neta_musd"))
    utilidad_bruta_ttm = _ttm(series.get("utilidad_bruta_musd"))
    dep_amort_ttm = _ttm(series.get("dep_amortizacion_musd"))
    eps_ttm = _ttm(series.get("eps_gaap"))
    dividendo_ttm = _ttm(series.get("dividendo_por_accion"))

    ebitda_ttm = (
        op_income_ttm + dep_amort_ttm if op_income_ttm is not None and dep_amort_ttm is not None else None
    )

    margen_operativo = series.get("margen_operativo") or []
    margen_ebit_pct = margen_operativo[-1]["valor"] if margen_operativo else None

    # Todo lo de balance viene en USD crudo (edgar._obtener_valor_instante), se pasa a
    # MUSD acá para que combine directo con las series de fundamentales (ya en MUSD).
    patrimonio_musd = balance.get("patrimonio") / 1_000_000 if balance.get("patrimonio") else None
    deuda_lp_musd = (balance.get("deuda_largo_plazo") or 0) / 1_000_000
    deuda_cp_musd = (balance.get("deuda_corto_plazo") or 0) / 1_000_000
    caja_musd = (balance.get("caja") or 0) / 1_000_000
    activos_musd = balance.get("activos_totales") / 1_000_000 if balance.get("activos_totales") else None
    pasivos_corr_musd = (
        balance.get("pasivos_corrientes") / 1_000_000 if balance.get("pasivos_corrientes") else None
    )
    acciones = balance.get("acciones_en_circulacion")

    deuda_total_musd = deuda_lp_musd + deuda_cp_musd
    deuda_neta_musd = deuda_total_musd - caja_musd

    # Igual criterio que radar.evaluar_sana(): en bancos la deuda es parte del modelo de
    # negocio (captan depósitos), no una señal de salud — None en vez de un ratio que se
    # leería como "alto" siempre y confundiría más de lo que ayuda.
    deuda_patrimonio = (
        None if ticker in radar.BANCOS else (deuda_total_musd / patrimonio_musd if patrimonio_musd else None)
    )

    market_cap_musd = precio * acciones / 1_000_000 if acciones else None
    enterprise_value_musd = market_cap_musd + deuda_neta_musd if market_cap_musd is not None else None

    margen_bruto_pct = (
        utilidad_bruta_ttm / ingresos_ttm * 100
        if utilidad_bruta_ttm is not None and ingresos_ttm
        else None
    )
    roa_pct = (
        utilidad_neta_ttm / activos_musd * 100
        if utilidad_neta_ttm is not None and activos_musd
        else None
    )
    roe_pct = (
        utilidad_neta_ttm / patrimonio_musd * 100
        if utilidad_neta_ttm is not None and patrimonio_musd
        else None
    )

    # ROIC simplificado: EBIT / capital invertido, SIN ajuste por tasa de impuesto (no
    # tenemos el tag de impuestos pagados) — es una aproximación honesta, no el ROIC
    # "de libro" con NOPAT. Capital invertido = deuda total + patrimonio - caja.
    capital_invertido_musd = (
        deuda_total_musd + patrimonio_musd - caja_musd if patrimonio_musd is not None else None
    )
    roic_pct = (
        op_income_ttm / capital_invertido_musd * 100
        if op_income_ttm is not None and capital_invertido_musd
        else None
    )
    roce_pct = (
        op_income_ttm / (activos_musd - pasivos_corr_musd) * 100
        if op_income_ttm is not None
        and activos_musd is not None
        and pasivos_corr_musd is not None
        and (activos_musd - pasivos_corr_musd) != 0
        else None
    )

    pe = precio / eps_ttm if eps_ttm and eps_ttm > 0 else None
    ev_ingresos = (
        enterprise_value_musd / ingresos_ttm
        if enterprise_value_musd is not None and ingresos_ttm
        else None
    )
    ev_ebitda = (
        enterprise_value_musd / ebitda_ttm
        if enterprise_value_musd is not None and ebitda_ttm
        else None
    )
    p_vl = (
        market_cap_musd / patrimonio_musd
        if market_cap_musd is not None and patrimonio_musd
        else None
    )
    dividend_yield_pct = dividendo_ttm / precio * 100 if dividendo_ttm and precio else None
    payout_ratio_pct = (
        dividendo_ttm / eps_ttm * 100 if dividendo_ttm is not None and eps_ttm else None
    )

    extremos_52s = radar.maximo_minimo_52s(hist_ticker, ahora)
    maximo_52s, minimo_52s = extremos_52s if extremos_52s else (None, None)

    beta = calcular_beta(hist_ticker, hist_mercado) if hist_ticker and hist_mercado else None

    return {
        "market_cap_musd": market_cap_musd,
        "enterprise_value_musd": enterprise_value_musd,
        "deuda_neta_musd": deuda_neta_musd,
        "deuda_neta_ebitda": deuda_neta_musd / ebitda_ttm if ebitda_ttm else None,
        "deuda_patrimonio": round(deuda_patrimonio, 2) if deuda_patrimonio is not None else None,
        "margen_bruto_pct": margen_bruto_pct,
        "margen_ebit_pct": margen_ebit_pct,
        "roa_pct": roa_pct,
        "roe_pct": roe_pct,
        "roic_pct": roic_pct,
        "roce_pct": roce_pct,
        "pe": pe,
        "ev_ingresos": ev_ingresos,
        "ev_ebitda": ev_ebitda,
        "p_vl": p_vl,
        "dividend_yield_pct": dividend_yield_pct,
        "payout_ratio_pct": payout_ratio_pct,
        "maximo_52s": maximo_52s,
        "minimo_52s": minimo_52s,
        "beta": beta,
    }
