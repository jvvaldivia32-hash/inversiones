import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import amigos, prices  # noqa: E402


def test_obtener_datos_tickers_ok(monkeypatch):
    def _cotizacion_falsa(ticker):
        return {"precio": 100.0, "var_dia_pct": 1.5, "cierre_anterior": 98.5}

    monkeypatch.setattr(prices, "obtener_cotizacion", _cotizacion_falsa)
    resultado = amigos.obtener_datos_tickers(["NVDA", "TSLA"])
    assert resultado == [
        {"ticker": "NVDA", "precio": 100.0, "var_dia_pct": 1.5},
        {"ticker": "TSLA", "precio": 100.0, "var_dia_pct": 1.5},
    ]


def test_obtener_datos_tickers_respeta_el_tope(monkeypatch):
    monkeypatch.setattr(
        prices, "obtener_cotizacion", lambda t: {"precio": 1, "var_dia_pct": 1, "cierre_anterior": 1}
    )
    resultado = amigos.obtener_datos_tickers(["A", "B", "C", "D"])
    assert len(resultado) == amigos.MAX_TICKERS_POR_AMIGO


def test_obtener_datos_tickers_un_ticker_roto_no_tumba_los_demas(monkeypatch):
    def _cotizacion(ticker):
        if ticker == "ROTO":
            raise prices.FinnhubError("sin datos")
        return {"precio": 50.0, "var_dia_pct": -2.0, "cierre_anterior": 51.0}

    monkeypatch.setattr(prices, "obtener_cotizacion", _cotizacion)
    resultado = amigos.obtener_datos_tickers(["ROTO", "MCD"])
    assert resultado == [{"ticker": "MCD", "precio": 50.0, "var_dia_pct": -2.0}]


def test_obtener_datos_tickers_lista_vacia():
    assert amigos.obtener_datos_tickers([]) == []


def test_obtener_recap_palabra_clave_parsea_y_recorta(monkeypatch):
    articulos_falsos = [
        {"titular": f"Titular {i}", "medio": "Medio", "url": f"https://ejemplo.com/{i}"}
        for i in range(10)
    ]
    monkeypatch.setattr(amigos.rss, "leer_feed", lambda url, medio, dominio: articulos_falsos)
    resultado = amigos.obtener_recap_palabra_clave("litio")
    assert len(resultado) == amigos.MAX_TITULARES_RECAP
    assert resultado[0] == {"titular": "Titular 0", "medio": "Medio", "url": "https://ejemplo.com/0"}


def test_obtener_recap_palabra_clave_vacia_no_llama_al_feed(monkeypatch):
    llamado = []
    monkeypatch.setattr(amigos.rss, "leer_feed", lambda *a, **k: llamado.append(1) or [])
    resultado = amigos.obtener_recap_palabra_clave("")
    assert resultado == []
    assert llamado == []


def test_obtener_recap_palabra_clave_feed_vacio(monkeypatch):
    monkeypatch.setattr(amigos.rss, "leer_feed", lambda url, medio, dominio: [])
    assert amigos.obtener_recap_palabra_clave("litio") == []
