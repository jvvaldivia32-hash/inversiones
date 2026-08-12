import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import noticias


def _articulo(titular, url, medio="Medio", grupo="Grupo", lean="centro"):
    return {
        "titular": titular,
        "extracto": "",
        "medio": medio,
        "grupo": grupo,
        "lean": lean,
        "url": url,
        "fecha": "2026-08-12T00:00:00",
    }


def test_es_economico_detecta_palabras_clave():
    assert noticias._es_economico("La Fed sube las tasas de interés") is True
    assert noticias._es_economico("Un gato rescata a un bombero") is False


def test_envolver_historia_shape():
    a = _articulo("Titular", "https://x.com/1")
    h = noticias._envolver_historia(a)
    assert h["titulo_neutral"] == "Titular"
    assert h["resumen"] == ""
    assert h["cobertura_unilateral"] is True
    assert h["articulos"] == [a]
    assert h["leans_presentes"] == ["centro"]
    assert h["grupos_presentes"] == ["Grupo"]


def test_recolectar_bloques_separa_mundo_de_actualidad(monkeypatch):
    def leer_feed_falso(url, medio, dominio):
        if "mundo" in url:
            return [
                _articulo("La Fed mantiene las tasas", "https://x.com/econ"),
                _articulo("Terremoto sacude la region", "https://x.com/otro"),
            ]
        return [_articulo("Noticia de Chile", "https://x.com/chile")]

    monkeypatch.setattr(noticias.feeds, "FEEDS_MUNDO", [("https://mundo.com/feed", "M", "m.com")])
    monkeypatch.setattr(noticias.feeds, "FEEDS_CHILE", [("https://chile.com/feed", "C", "c.com")])
    monkeypatch.setattr(noticias.rss, "leer_feed", leer_feed_falso)

    mundo, chile, actualidad, errores = noticias.recolectar_bloques()
    assert len(mundo) == 1
    assert mundo[0]["titulo_neutral"] == "La Fed mantiene las tasas"
    assert len(actualidad) == 1
    assert actualidad[0]["titular"] == "Terremoto sacude la region"
    assert len(chile) == 1
    assert errores == []


def test_recolectar_bloques_deduplica_por_url(monkeypatch):
    def leer_feed_falso(url, medio, dominio):
        return [_articulo("Repetida", "https://x.com/misma")]

    monkeypatch.setattr(
        noticias.feeds,
        "FEEDS_MUNDO",
        [("https://a.com/feed", "A", "a.com"), ("https://b.com/feed", "B", "b.com")],
    )
    monkeypatch.setattr(noticias.feeds, "FEEDS_CHILE", [])
    monkeypatch.setattr(noticias.rss, "leer_feed", leer_feed_falso)

    mundo, chile, actualidad, errores = noticias.recolectar_bloques()
    assert len(mundo) + len(actualidad) == 1


def test_recolectar_bloques_registra_error_si_feed_vacio(monkeypatch):
    monkeypatch.setattr(noticias.feeds, "FEEDS_MUNDO", [("https://a.com/feed", "A", "a.com")])
    monkeypatch.setattr(noticias.feeds, "FEEDS_CHILE", [])
    monkeypatch.setattr(noticias.rss, "leer_feed", lambda url, medio, dominio: [])

    _, _, _, errores = noticias.recolectar_bloques()
    assert len(errores) == 1
    assert "A" in errores[0]
