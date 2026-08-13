import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import noticias


def _articulo(titular, url, medio="Medio", grupo="Grupo", lean="centro", snippet=""):
    return {
        "titular": titular,
        "extracto": "",
        "medio": medio,
        "grupo": grupo,
        "lean": lean,
        "url": url,
        "fecha": "2026-08-12T00:00:00+00:00",
        "_snippet_original": snippet,
    }


def test_es_economico_detecta_palabras_clave():
    assert noticias._es_economico("La Fed sube las tasas de interés") is True
    assert noticias._es_economico("Un gato rescata a un bombero") is False


def test_es_economico_detecta_ipo():
    # Encontrado en vivo (2026-08-13): "Anthropic's anticipated $2tn IPO" no matcheaba
    # ninguna palabra de la lista original — caía a Actualidad (tope 5) en vez de Mundo
    # (tope 8) y se perdía por volumen.
    assert noticias._es_economico("Anthropic's anticipated $2tn IPO") is True


def test_articulo_publico_saca_campos_internos():
    a = _articulo("Titular", "https://x.com/1", snippet="crudo")
    publico = noticias._articulo_publico(a)
    assert "_snippet_original" not in publico
    assert publico["titular"] == "Titular"


def test_agrupar_por_keywords_junta_por_sustantivos_propios_compartidos():
    articulos = [
        _articulo("La Fed y Jerome Powell mantienen las tasas", "https://x.com/1"),
        _articulo("Jerome Powell y la Fed no suben tasas", "https://x.com/2"),
        _articulo("Un terremoto sacude la región", "https://x.com/3"),
    ]
    grupos = noticias._agrupar_por_keywords(articulos)
    tamaños = sorted(len(indices) for _, indices in grupos)
    assert tamaños == [1, 2]


def test_construir_historia_cobertura_unilateral_con_un_solo_grupo():
    pool = [
        _articulo("A", "https://x.com/1", grupo="Reuters"),
        _articulo("B", "https://x.com/2", grupo="Reuters"),
    ]
    h = noticias._construir_historia("Título neutral", [0, 1], pool, "un resumen")
    assert h["titulo_neutral"] == "Título neutral"
    assert h["resumen"] == "un resumen"
    assert h["cobertura_unilateral"] is True
    assert h["grupos_presentes"] == ["Reuters"]
    assert len(h["articulos"]) == 2


def test_construir_historia_cobertura_no_unilateral_con_grupos_distintos():
    pool = [
        _articulo("A", "https://x.com/1", grupo="Reuters"),
        _articulo("B", "https://x.com/2", grupo="El Mercurio"),
    ]
    h = noticias._construir_historia("Título neutral", [0, 1], pool, None)
    assert h["cobertura_unilateral"] is False
    assert h["resumen"] == ""
    assert set(h["grupos_presentes"]) == {"Reuters", "El Mercurio"}


def test_construir_bloque_usa_gemini_cuando_responde(monkeypatch):
    pool = [
        _articulo("Fed mantiene tasas", "https://x.com/1", grupo="Reuters", snippet="s1"),
        _articulo("Powell no sube tasas", "https://x.com/2", grupo="AP", snippet="s2"),
    ]
    monkeypatch.setattr(
        noticias.gemini, "agrupar_historias", lambda titulares: [("La Fed mantiene tasas", [0, 1])]
    )
    monkeypatch.setattr(noticias.gemini, "reescribir_resumenes", lambda items: ["resumen ok"])

    bloque = noticias._construir_bloque(pool, tope=8)
    assert len(bloque) == 1
    assert bloque[0]["titulo_neutral"] == "La Fed mantiene tasas"
    assert bloque[0]["resumen"] == "resumen ok"
    assert bloque[0]["cobertura_unilateral"] is False


def test_construir_bloque_cae_a_keywords_si_gemini_falla(monkeypatch):
    pool = [_articulo("Titular sin agrupar", "https://x.com/1")]
    monkeypatch.setattr(noticias.gemini, "agrupar_historias", lambda titulares: None)
    monkeypatch.setattr(noticias.gemini, "reescribir_resumenes", lambda items: None)

    bloque = noticias._construir_bloque(pool, tope=8)
    assert len(bloque) == 1
    assert bloque[0]["titulo_neutral"] == "Titular sin agrupar"
    assert bloque[0]["resumen"] == ""


def test_construir_bloque_respeta_el_tope_despues_de_agrupar(monkeypatch):
    pool = [_articulo(f"T{i}", f"https://x.com/{i}") for i in range(5)]
    monkeypatch.setattr(noticias.gemini, "agrupar_historias", lambda titulares: None)
    monkeypatch.setattr(noticias.gemini, "reescribir_resumenes", lambda items: None)

    bloque = noticias._construir_bloque(pool, tope=2)
    assert len(bloque) == 2


def test_construir_bloque_vacio_no_llama_a_gemini(monkeypatch):
    llamado = []
    monkeypatch.setattr(
        noticias.gemini, "agrupar_historias", lambda titulares: llamado.append(1) or None
    )
    assert noticias._construir_bloque([], tope=8) == []
    assert llamado == []


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
    monkeypatch.setattr(noticias.gemini, "agrupar_historias", lambda titulares: None)
    monkeypatch.setattr(noticias.gemini, "reescribir_resumenes", lambda items: None)

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
    monkeypatch.setattr(noticias.gemini, "agrupar_historias", lambda titulares: None)
    monkeypatch.setattr(noticias.gemini, "reescribir_resumenes", lambda items: None)

    mundo, chile, actualidad, errores = noticias.recolectar_bloques()
    assert len(mundo) + len(actualidad) == 1


def test_recolectar_bloques_registra_error_si_feed_vacio(monkeypatch):
    monkeypatch.setattr(noticias.feeds, "FEEDS_MUNDO", [("https://a.com/feed", "A", "a.com")])
    monkeypatch.setattr(noticias.feeds, "FEEDS_CHILE", [])
    monkeypatch.setattr(noticias.rss, "leer_feed", lambda url, medio, dominio: [])
    monkeypatch.setattr(noticias.gemini, "agrupar_historias", lambda titulares: None)
    monkeypatch.setattr(noticias.gemini, "reescribir_resumenes", lambda items: None)

    _, _, _, errores = noticias.recolectar_bloques()
    assert len(errores) == 1
    assert "A" in errores[0]


def test_noticias_ticker_sin_articulos_no_llama_a_gemini(monkeypatch):
    llamado = []
    monkeypatch.setattr(noticias.rss, "leer_feed", lambda url, medio, dominio: [])
    monkeypatch.setattr(
        noticias.gemini, "reescribir_resumenes", lambda items: llamado.append(1) or None
    )
    assert noticias.noticias_ticker("AAPL") == []
    assert llamado == []


def test_noticias_ticker_rellena_extracto_desde_gemini(monkeypatch):
    monkeypatch.setattr(
        noticias.rss,
        "leer_feed",
        lambda url, medio, dominio: [_articulo("Titular", "https://x.com/1", snippet="original")],
    )
    monkeypatch.setattr(noticias.gemini, "reescribir_resumenes", lambda items: ["reescrito"])

    resultado = noticias.noticias_ticker("AAPL")
    assert len(resultado) == 1
    assert resultado[0]["extracto"] == "reescrito"
    assert "_snippet_original" not in resultado[0]


def test_noticias_ticker_extracto_vacio_si_gemini_falla(monkeypatch):
    monkeypatch.setattr(
        noticias.rss,
        "leer_feed",
        lambda url, medio, dominio: [_articulo("Titular", "https://x.com/1", snippet="original")],
    )
    monkeypatch.setattr(noticias.gemini, "reescribir_resumenes", lambda items: None)

    resultado = noticias.noticias_ticker("AAPL")
    assert resultado[0]["extracto"] == ""
