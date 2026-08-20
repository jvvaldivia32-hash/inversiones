import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import metricas_avanzadas  # noqa: E402


def _serie_constante(nombre: str, valor: float, trimestres: int = 4) -> list[dict]:
    return [{"periodo": f"FY24Q{i + 1}", "valor": valor} for i in range(trimestres)]


def _fundamentales_sinteticos() -> dict:
    return {
        "series": {
            "ingresos_musd": _serie_constante("ingresos", 100),
            "op_income_musd": _serie_constante("op_income", 20),
            "utilidad_neta_musd": _serie_constante("utilidad_neta", 15),
            "utilidad_bruta_musd": _serie_constante("utilidad_bruta", 50),
            "dep_amortizacion_musd": _serie_constante("dep", 5),
            "eps_gaap": _serie_constante("eps", 2.5),
            "dividendo_por_accion": _serie_constante("div", 0.5),
            "margen_operativo": [{"periodo": "FY24Q4", "valor": 25}],
        }
    }


def _balance_sintetico() -> dict:
    return {
        "patrimonio": 500_000_000,
        "deuda_largo_plazo": 100_000_000,
        "deuda_corto_plazo": 50_000_000,
        "caja": 30_000_000,
        "activos_totales": 800_000_000,
        "pasivos_corrientes": 200_000_000,
        "acciones_en_circulacion": 10_000_000,
    }


def _serie_precio(valores: list[float], inicio: datetime.date) -> list[dict]:
    return [
        {"ts": (inicio + datetime.timedelta(days=i)).isoformat() + "T00:00:00", "valor": v}
        for i, v in enumerate(valores)
    ]


def test_ttm_con_cuatro_trimestres():
    assert metricas_avanzadas._ttm(_serie_constante("x", 10)) == 40


def test_ttm_insuficientes_puntos_da_none():
    assert metricas_avanzadas._ttm([{"periodo": "FY24Q4", "valor": 10}]) is None


def test_ttm_serie_vacia_o_none_da_none():
    assert metricas_avanzadas._ttm([]) is None
    assert metricas_avanzadas._ttm(None) is None


def test_calcular_metricas_sin_datos_da_none():
    ahora = datetime.datetime(2026, 8, 14, tzinfo=datetime.timezone.utc)
    assert metricas_avanzadas.calcular_metricas("XYZ", None, None, 100, [], [], ahora) is None


def test_calcular_metricas_completo(monkeypatch):
    monkeypatch.setattr(
        metricas_avanzadas.radar, "maximo_minimo_52s", lambda serie, ahora: (150.0, 80.0)
    )
    ahora = datetime.datetime(2026, 8, 14, tzinfo=datetime.timezone.utc)

    resultado = metricas_avanzadas.calcular_metricas(
        "PEP", _fundamentales_sinteticos(), _balance_sintetico(), 100.0, [], [], ahora
    )

    assert resultado["market_cap_musd"] == 1000.0
    assert resultado["enterprise_value_musd"] == 1120.0
    assert resultado["deuda_neta_musd"] == 120.0
    assert round(resultado["deuda_neta_ebitda"], 2) == 1.2
    assert resultado["deuda_patrimonio"] == 0.3
    assert resultado["margen_bruto_pct"] == 50.0
    assert resultado["margen_ebit_pct"] == 25
    assert resultado["roa_pct"] == 7.5
    assert resultado["roe_pct"] == 12.0
    assert round(resultado["roic_pct"], 2) == round(80 / 620 * 100, 2)
    assert round(resultado["roce_pct"], 2) == round(80 / 600 * 100, 2)
    assert resultado["pe"] == 10.0
    assert resultado["ev_ingresos"] == 2.8
    assert round(resultado["ev_ebitda"], 2) == 11.2
    assert resultado["p_vl"] == 2.0
    assert resultado["dividend_yield_pct"] == 2.0
    assert resultado["payout_ratio_pct"] == 20.0
    assert resultado["maximo_52s"] == 150.0
    assert resultado["minimo_52s"] == 80.0
    assert resultado["beta"] is None  # sin histórico real en este test


def test_calcular_metricas_campo_faltante_no_tumba_los_demas(monkeypatch):
    """Sin acciones en circulación (empresa que no tagea el dato dei), Market Cap/EV/P-VL
    quedan en None pero ROE/ROA/márgenes siguen calculándose — no todo o nada."""
    monkeypatch.setattr(
        metricas_avanzadas.radar, "maximo_minimo_52s", lambda serie, ahora: None
    )
    ahora = datetime.datetime(2026, 8, 14, tzinfo=datetime.timezone.utc)
    balance = _balance_sintetico()
    balance["acciones_en_circulacion"] = None

    resultado = metricas_avanzadas.calcular_metricas(
        "XYZ", _fundamentales_sinteticos(), balance, 100.0, [], [], ahora
    )

    assert resultado["market_cap_musd"] is None
    assert resultado["enterprise_value_musd"] is None
    assert resultado["p_vl"] is None
    assert resultado["roe_pct"] == 12.0
    assert resultado["roa_pct"] == 7.5
    assert resultado["maximo_52s"] is None
    assert resultado["minimo_52s"] is None


def test_calcular_metricas_banco_deuda_patrimonio_da_none(monkeypatch):
    """Igual criterio que radar.evaluar_sana(): en bancos la deuda es el modelo de negocio,
    no una señal de salud — el ratio no se calcula para no leerse como "alto" siempre."""
    monkeypatch.setattr(
        metricas_avanzadas.radar, "maximo_minimo_52s", lambda serie, ahora: None
    )
    ahora = datetime.datetime(2026, 8, 14, tzinfo=datetime.timezone.utc)

    resultado = metricas_avanzadas.calcular_metricas(
        "JPM", _fundamentales_sinteticos(), _balance_sintetico(), 100.0, [], [], ahora
    )

    assert resultado["deuda_patrimonio"] is None


def test_calcular_beta_serie_corta_da_none():
    ahora_base = datetime.date(2026, 1, 1)
    corta = _serie_precio([100, 101, 102], ahora_base)
    mercado = _serie_precio([50, 50.5, 51], ahora_base)
    assert metricas_avanzadas.calcular_beta(corta, mercado) is None


def test_calcular_beta_el_doble_de_volatil_que_el_mercado():
    """Ticker sintético cuyo retorno diario es siempre el doble del retorno del mercado
    -> beta debería salir ~2.0."""
    dias = 80
    inicio = datetime.date(2026, 1, 1)
    valores_mercado = [100.0]
    valores_ticker = [50.0]
    # Retornos alternados +1%/-1% para tener varianza real, no una línea recta.
    for i in range(dias - 1):
        retorno_mercado = 0.01 if i % 2 == 0 else -0.008
        valores_mercado.append(valores_mercado[-1] * (1 + retorno_mercado))
        valores_ticker.append(valores_ticker[-1] * (1 + 2 * retorno_mercado))

    serie_ticker = _serie_precio(valores_ticker, inicio)
    serie_mercado = _serie_precio(valores_mercado, inicio)

    beta = metricas_avanzadas.calcular_beta(serie_ticker, serie_mercado)
    assert beta is not None
    assert round(beta, 3) == 2.0
