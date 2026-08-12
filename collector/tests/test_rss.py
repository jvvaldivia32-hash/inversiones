import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sources"))

from sources import rss


class _FeedFalso:
    def __init__(self, entries):
        self.entries = entries


def test_leer_feed_parsea_articulos(monkeypatch):
    entradas = [
        {
            "title": "Titular uno",
            "link": "https://example.com/1",
            "published_parsed": (2026, 8, 12, 10, 0, 0, 0, 0, 0),
        },
        {"title": "Titular dos", "link": "https://example.com/2", "published_parsed": None},
    ]
    monkeypatch.setattr(rss.feedparser, "parse", lambda url, agent=None: _FeedFalso(entradas))
    articulos = rss.leer_feed("https://fake.com/feed", "Medio Falso", "un-dominio-sin-clasificar.com")
    assert len(articulos) == 2
    assert articulos[0]["titular"] == "Titular uno"
    assert articulos[0]["url"] == "https://example.com/1"
    assert articulos[0]["extracto"] == ""
    assert articulos[0]["fecha"].startswith("2026-08-12")


def test_leer_feed_descarta_entradas_sin_titulo_o_link(monkeypatch):
    entradas = [{"title": "", "link": "https://example.com/1"}, {"title": "Ok", "link": ""}]
    monkeypatch.setattr(rss.feedparser, "parse", lambda url, agent=None: _FeedFalso(entradas))
    assert rss.leer_feed("https://fake.com/feed", "Medio", "dominio.com") == []


def test_leer_feed_sin_entradas_devuelve_vacio(monkeypatch):
    monkeypatch.setattr(rss.feedparser, "parse", lambda url, agent=None: _FeedFalso([]))
    assert rss.leer_feed("https://fake.com/feed", "Medio", "dominio.com") == []


def test_leer_feed_error_devuelve_vacio(monkeypatch):
    def levantar(url, agent=None):
        raise Exception("boom")

    monkeypatch.setattr(rss.feedparser, "parse", levantar)
    assert rss.leer_feed("https://fake.com/feed", "Medio", "dominio.com") == []
