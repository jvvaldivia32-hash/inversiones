import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import edgar, segmentos


def test_html_a_texto_saca_tags_script_y_style():
    html = "<html><head><style>.x{color:red}</style></head><body><p>Hola <b>mundo</b></p><script>alert(1)</script></body></html>"
    assert "color:red" not in segmentos._html_a_texto(html)
    assert "alert(1)" not in segmentos._html_a_texto(html)
    assert "Hola mundo" in segmentos._html_a_texto(html)


def test_html_a_texto_colapsa_espacios_y_saltos_de_linea():
    html = "<p>Uno</p>\n\n\n\n<p>Dos   con   espacios</p>"
    texto = segmentos._html_a_texto(html)
    assert "\n\n\n" not in texto
    assert "Dos con espacios" in texto


def test_es_exhibit_991_reconoce_variantes_reales():
    assert segmentos._es_exhibit_991("msft-ex99_1.htm")
    assert segmentos._es_exhibit_991("d159922dex991.htm")
    assert segmentos._es_exhibit_991("a8-kex991q3202606272026.htm")
    assert segmentos._es_exhibit_991("exhibit991-6302026.htm")
    assert not segmentos._es_exhibit_991("mcd-20260804.htm")
    assert not segmentos._es_exhibit_991("exhibit992-6302026.htm")


def test_buscar_exhibit_991_toma_el_8k_de_resultados_mas_reciente(monkeypatch):
    def _request_falso(url):
        if "submissions" in url:
            return {
                "filings": {
                    "recent": {
                        "form": ["8-K", "8-K", "10-Q"],
                        "items": ["5.02", "2.02,9.01", ""],
                        "accessionNumber": ["a1", "a2", "a3"],
                    }
                }
            }
        assert "a2" in url
        return {"directory": {"item": [{"name": "irrelevante.htm"}, {"name": "ex99_1.htm"}]}}

    monkeypatch.setattr(edgar, "_request", _request_falso)
    resultado = segmentos._buscar_exhibit_991("0000789019")
    assert resultado is not None
    accession, url = resultado
    assert accession == "a2"
    assert url.endswith("ex99_1.htm")


def test_buscar_exhibit_991_none_si_no_hay_8k_de_resultados(monkeypatch):
    monkeypatch.setattr(
        edgar,
        "_request",
        lambda url: {"filings": {"recent": {"form": ["10-Q"], "items": [""], "accessionNumber": ["a1"]}}},
    )
    assert segmentos._buscar_exhibit_991("0000789019") is None


def test_buscar_exhibit_991_none_si_ningun_documento_calza(monkeypatch):
    def _request_falso(url):
        if "submissions" in url:
            return {
                "filings": {
                    "recent": {
                        "form": ["8-K"],
                        "items": ["2.02"],
                        "accessionNumber": ["a1"],
                    }
                }
            }
        return {"directory": {"item": [{"name": "mcd-20260804.htm"}]}}

    monkeypatch.setattr(edgar, "_request", _request_falso)
    assert segmentos._buscar_exhibit_991("0000063908") is None


def test_obtener_segmentos_sin_cambios_devuelve_none(monkeypatch):
    monkeypatch.setattr(segmentos, "_buscar_exhibit_991", lambda cik: ("a2", "http://x"))
    assert segmentos.obtener_segmentos("cik", "a2") is None


def test_obtener_segmentos_sin_8k_devuelve_none(monkeypatch):
    monkeypatch.setattr(segmentos, "_buscar_exhibit_991", lambda cik: None)
    assert segmentos.obtener_segmentos("cik", None) is None


def test_obtener_segmentos_arma_el_shape(monkeypatch):
    monkeypatch.setattr(segmentos, "_buscar_exhibit_991", lambda cik: ("a2", "http://x"))
    monkeypatch.setattr(edgar, "request_texto", lambda url: "<p>Azure revenue grew 43%.</p>")
    monkeypatch.setattr(
        segmentos.gemini,
        "extraer_segmentos",
        lambda texto: [{"nombre": "Azure", "var_pct": 43, "cita": "Azure revenue grew 43%."}],
    )
    resultado = segmentos.obtener_segmentos("cik", None)
    assert resultado == {
        "segmentos": [{"nombre": "Azure", "var_pct": 43, "cita": "Azure revenue grew 43%."}],
        "_accession": "a2",
    }


def test_obtener_segmentos_none_si_gemini_falla(monkeypatch):
    monkeypatch.setattr(segmentos, "_buscar_exhibit_991", lambda cik: ("a2", "http://x"))
    monkeypatch.setattr(edgar, "request_texto", lambda url: "<p>texto</p>")
    monkeypatch.setattr(segmentos.gemini, "extraer_segmentos", lambda texto: None)
    assert segmentos.obtener_segmentos("cik", None) is None
