import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import amigos, prices  # noqa: E402


def test_obtener_dato_ticker_ok(monkeypatch):
    monkeypatch.setattr(
        prices, "obtener_cotizacion", lambda t: {"precio": 100.0, "var_dia_pct": 1.5, "cierre_anterior": 98.5}
    )
    assert amigos.obtener_dato_ticker("NVDA") == {"precio": 100.0, "var_dia_pct": 1.5}


def test_obtener_dato_ticker_roto_da_none(monkeypatch):
    def _cotizacion(ticker):
        raise prices.FinnhubError("sin datos")

    monkeypatch.setattr(prices, "obtener_cotizacion", _cotizacion)
    assert amigos.obtener_dato_ticker("ROTO") is None


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
