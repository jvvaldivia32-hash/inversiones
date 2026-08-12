import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import prices


def test_obtener_cotizacion_sin_key(monkeypatch):
    monkeypatch.delenv("FINNHUB_KEY", raising=False)
    with pytest.raises(prices.FinnhubError, match="FINNHUB_KEY"):
        prices.obtener_cotizacion("MSFT")


def test_obtener_cotizacion_parsea_precio(monkeypatch):
    monkeypatch.setenv("FINNHUB_KEY", "fake")
    monkeypatch.setattr(
        prices,
        "_request",
        lambda ruta, params: {"c": 504.47, "d": 3.1, "dp": 0.62, "pc": 501.37},
    )
    resultado = prices.obtener_cotizacion("MSFT")
    assert resultado == {"precio": 504.47, "var_dia_pct": 0.62, "cierre_anterior": 501.37}


def test_obtener_cotizacion_sin_datos_levanta_error(monkeypatch):
    monkeypatch.setenv("FINNHUB_KEY", "fake")
    monkeypatch.setattr(prices, "_request", lambda ruta, params: {"c": 0, "pc": 0})
    with pytest.raises(prices.FinnhubError, match="Sin datos"):
        prices.obtener_cotizacion("TICKERINVENTADO")


def test_obtener_velas_parsea_serie(monkeypatch):
    monkeypatch.setenv("FINNHUB_KEY", "fake")
    monkeypatch.setattr(
        prices,
        "_request",
        lambda ruta, params: {
            "s": "ok",
            "t": [1754784000, 1754870400],
            "c": [500.1, 504.47],
        },
    )
    velas = prices.obtener_velas("MSFT", dias=30)
    assert velas == [
        {"fecha": "2025-08-10", "valor": 500.1},
        {"fecha": "2025-08-11", "valor": 504.47},
    ]


def test_obtener_velas_sin_datos_devuelve_lista_vacia(monkeypatch):
    monkeypatch.setenv("FINNHUB_KEY", "fake")
    monkeypatch.setattr(prices, "_request", lambda ruta, params: {"s": "no_data"})
    assert prices.obtener_velas("TICKERINVENTADO", dias=30) == []
