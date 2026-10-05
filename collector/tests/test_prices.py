import sys
from pathlib import Path

import io
import urllib.error

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


def _http_429():
    return urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_request_reintenta_tras_429(monkeypatch):
    monkeypatch.setenv("FINNHUB_KEY", "fake")
    esperas = []
    monkeypatch.setattr(prices.time, "sleep", esperas.append)
    respuestas = [_http_429(), _Resp(b'{"c": 1.5, "pc": 1.4}')]

    def urlopen(url, timeout):
        r = respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(prices.urllib.request, "urlopen", urlopen)
    assert prices.obtener_cotizacion("ORCL")["precio"] == 1.5
    assert esperas == [prices.ESPERA_429_S]


def test_request_se_rinde_tras_varios_429(monkeypatch):
    monkeypatch.setenv("FINNHUB_KEY", "fake")
    monkeypatch.setattr(prices.time, "sleep", lambda s: None)

    def urlopen(url, timeout):
        raise _http_429()

    monkeypatch.setattr(prices.urllib.request, "urlopen", urlopen)
    with pytest.raises(prices.FinnhubError, match="429"):
        prices.obtener_cotizacion("ORCL")
