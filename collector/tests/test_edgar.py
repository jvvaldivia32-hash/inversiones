import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import edgar


def test_headers_sin_user_agent_levanta_error(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    with pytest.raises(edgar.EdgarError, match="SEC_USER_AGENT"):
        edgar._headers()


def test_headers_con_user_agent(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "José <jose@example.com>")
    assert edgar._headers() == {"User-Agent": "José <jose@example.com>"}


def _punto(fy, fp, val, start, end, filed, form="10-Q"):
    return {"fy": fy, "fp": fp, "val": val, "start": start, "end": end, "filed": filed, "form": form}


# Un año fiscal tipo MSFT (termina el 30 de junio): cada 10-Q trae el trimestre solo
# (~90 días) además del acumulado year-to-date. El 10-K solo trae el año completo.
def _trimestre(fy, fp, inicio, fin, val, filed):
    return _punto(fy, fp, val, inicio, fin, filed, form="10-Q")


def test_extraer_serie_usa_el_hecho_puntual_del_trimestre():
    puntos = [
        _trimestre(2026, "Q1", "2025-07-01", "2025-09-30", 77673, "2025-10-29"),
        # el mismo 10-Q también trae el acumulado YTD, que para Q1 coincide en valor
        # pero tiene distinta duración — no debería duplicar la entrada.
        _punto(2026, "Q2", 158946, "2025-07-01", "2025-12-31", "2026-01-28"),
        _trimestre(2026, "Q2", "2025-10-01", "2025-12-31", 81273, "2026-01-28"),
    ]
    data = {"units": {"USD": puntos}}
    serie = edgar._extraer_serie(data, "USD", 1)
    assert serie == [
        {"periodo": "FY26Q1", "valor": 77673},
        {"periodo": "FY26Q2", "valor": 81273},
    ]


def test_extraer_serie_deriva_q4_restando_el_acumulado_de_9_meses():
    puntos = [
        _punto(2026, "Q3", 241832, "2025-07-01", "2026-03-31", "2026-04-29", form="10-Q"),
        _punto(2026, "FY", 331839, "2025-07-01", "2026-06-30", "2026-07-29", form="10-K"),
    ]
    data = {"units": {"USD": puntos}}
    serie = edgar._extraer_serie(data, "USD", 1)
    assert {"periodo": "FY26Q4", "valor": 90007} in serie


def test_extraer_serie_duplicado_usa_etiqueta_del_mas_antiguo_y_valor_del_mas_nuevo():
    # El mismo trimestre (mismo start/end) reaparece un año después como comparativo en
    # otro 10-Q, con un `fy` que quedó pegado al año de ESE filing — no al real.
    puntos = [
        _trimestre(2024, "Q1", "2023-07-01", "2023-09-30", 56517, "2023-10-24"),
        _trimestre(2025, "Q1", "2023-07-01", "2023-09-30", 56517, "2024-10-30"),
    ]
    data = {"units": {"USD": puntos}}
    serie = edgar._extraer_serie(data, "USD", 1)
    assert serie == [{"periodo": "FY24Q1", "valor": 56517}]


def test_extraer_serie_ignora_form_no_trimestral():
    puntos = [_trimestre(2026, "Q1", "2026-01-01", "2026-03-31", 500, "2026-04-10")]
    puntos[0]["form"] = "8-K"
    data = {"units": {"USD": puntos}}
    assert edgar._extraer_serie(data, "USD", 1) == []


def test_extraer_serie_recorta_a_12_trimestres():
    # 4 años calendario de trimestres genéricos (16 en total) para probar el recorte.
    trimestres_por_anio = [
        ("Q1", "01-01", "03-31"),
        ("Q2", "04-01", "06-30"),
        ("Q3", "07-01", "09-30"),
        ("Q4", "10-01", "12-31"),
    ]
    puntos = [
        _trimestre(anio, fp, f"{anio}-{ini}", f"{anio}-{fin}", anio * 10 + n, f"{anio}-{fin[:2]}-15")
        for anio in (2023, 2024, 2025, 2026)
        for n, (fp, ini, fin) in enumerate(trimestres_por_anio, start=1)
    ]
    data = {"units": {"USD": puntos}}
    serie = edgar._extraer_serie(data, "USD", 1)
    assert len(serie) == 12
    assert serie[-1]["periodo"] == "FY26Q4"
    assert serie[0]["periodo"] == "FY24Q1"


def test_extraer_serie_convierte_a_millones():
    puntos = [_trimestre(2026, "Q1", "2025-07-01", "2025-09-30", 75_800_000_000, "2025-10-29")]
    data = {"units": {"USD": puntos}}
    serie = edgar._extraer_serie(data, "USD", 1_000_000)
    assert serie[0]["valor"] == 75800.0


def test_derivar_margen():
    ingresos = [{"periodo": "FY26Q1", "valor": 1000}]
    op_income = [{"periodo": "FY26Q1", "valor": 250}]
    assert edgar._derivar_margen(ingresos, op_income) == [{"periodo": "FY26Q1", "valor": 25.0}]


def test_derivar_margen_ignora_periodos_sin_match():
    op_income = [{"periodo": "FY26Q1", "valor": 250}]
    assert edgar._derivar_margen([], op_income) == []


def test_tiene_datos_recientes_true_si_hay_filed_dentro_de_la_ventana():
    import datetime

    hoy = datetime.date.today().isoformat()
    assert edgar._tiene_datos_recientes({"units": {"USD": [{"filed": hoy}]}}) is True


def test_tiene_datos_recientes_false_si_todo_es_viejo():
    assert edgar._tiene_datos_recientes({"units": {"USD": [{"filed": "2013-12-31"}]}}) is False


def test_obtener_fundamentales_campo_con_tag_obsoleto_queda_vacio(monkeypatch):
    monkeypatch.setattr(edgar, "_ultimo_accession", lambda cik: "accn")

    def _request_falso(url):
        if "EarningsPerShareDiluted" in url or "EarningsPerShareBasic" in url:
            return {"units": {"USD/shares": [_trimestre(2013, "Q4", "2013-10-01", "2013-12-31", 3035, "2014-03-03")]}}
        return {"units": {"USD": [_trimestre(2026, "Q4", "2026-04-01", "2026-06-30", 1_000_000, "2026-07-25")]}}

    monkeypatch.setattr(edgar, "_request", _request_falso)
    resultado = edgar.obtener_fundamentales("MSFT", edgar.CIK_POR_TICKER["MSFT"], None)
    assert resultado["series"]["eps_gaap"] == []


def test_ultimo_accession_toma_el_primer_10q_o_10k(monkeypatch):
    monkeypatch.setattr(
        edgar,
        "_request",
        lambda url: {
            "filings": {
                "recent": {
                    "form": ["8-K", "10-Q", "10-K"],
                    "accessionNumber": ["a1", "a2", "a3"],
                }
            }
        },
    )
    assert edgar._ultimo_accession("0000789019") == "a2"


def test_ultimo_accession_none_si_no_hay_filings_trimestrales(monkeypatch):
    monkeypatch.setattr(
        edgar,
        "_request",
        lambda url: {"filings": {"recent": {"form": ["8-K"], "accessionNumber": ["a1"]}}},
    )
    assert edgar._ultimo_accession("0000789019") is None


def test_obtener_fundamentales_sin_cambios_devuelve_none(monkeypatch):
    monkeypatch.setattr(edgar, "_ultimo_accession", lambda cik: "misma-accession")
    assert edgar.obtener_fundamentales("MSFT", edgar.CIK_POR_TICKER["MSFT"], "misma-accession") is None


def test_obtener_fundamentales_arma_el_shape_completo(monkeypatch):
    monkeypatch.setattr(edgar, "_ultimo_accession", lambda cik: "0000789019-26-000042")

    def _request_falso(url):
        if "RevenueFromContract" in url:
            return {"units": {"USD": [_trimestre(2026, "Q4", "2026-04-01", "2026-06-30", 90_007_000_000, "2026-07-25")]}}
        if "OperatingIncomeLoss" in url:
            return {"units": {"USD": [_trimestre(2026, "Q4", "2026-04-01", "2026-06-30", 40_603_000_000, "2026-07-25")]}}
        if "EarningsPerShareDiluted" in url:
            return {"units": {"USD/shares": [_trimestre(2026, "Q4", "2026-04-01", "2026-06-30", 4.81, "2026-07-25")]}}
        return {"units": {"USD": [_trimestre(2026, "Q4", "2026-04-01", "2026-06-30", 1_000_000, "2026-07-25")]}}

    monkeypatch.setattr(edgar, "_request", _request_falso)

    resultado = edgar.obtener_fundamentales("MSFT", edgar.CIK_POR_TICKER["MSFT"], None)
    assert resultado["periodo"] == "FY26Q4"
    assert resultado["_accession"] == "0000789019-26-000042"
    assert resultado["series"]["ingresos_musd"][0]["valor"] == 90007.0
    assert resultado["series"]["eps_gaap"][0]["valor"] == 4.81
    assert resultado["series"]["eps_non_gaap"] == []
    assert round(resultado["series"]["margen_operativo"][0]["valor"], 1) == 45.1
    assert "sec.gov" in resultado["fuente_url"]


def _instante(val, end, filed, form="10-K"):
    return {"val": val, "end": end, "filed": filed, "form": form}


def test_resolver_ciks_usa_el_indice_sec(monkeypatch):
    monkeypatch.setattr(
        edgar,
        "_request",
        lambda url: {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 1067983, "ticker": "BRK-B", "title": "Berkshire Hathaway"},
            "2": {"cik_str": 12345, "ticker": "XYZ", "title": "Algo SA"},
        },
    )
    resultado = edgar.resolver_ciks(["AAPL", "BRK.B", "XYZ", "NOEXISTE"])
    assert resultado == {"AAPL": "0000320193", "BRK.B": "0001067983", "XYZ": "0000012345"}


def test_resolver_ciks_prefiere_cik_por_ticker_ya_verificado(monkeypatch):
    monkeypatch.setattr(
        edgar,
        "_request",
        lambda url: {"0": {"cik_str": 999999999, "ticker": "AAPL", "title": "otro"}},
    )
    resultado = edgar.resolver_ciks(["AAPL"])
    assert resultado["AAPL"] == edgar.CIK_POR_TICKER["AAPL"]


def test_obtener_valor_instante_toma_el_end_mas_reciente(monkeypatch):
    monkeypatch.setattr(
        edgar,
        "_request",
        lambda url: {
            "units": {
                "USD": [
                    _instante(100, "2025-06-30", "2025-07-25"),
                    _instante(150, "2026-06-30", "2026-07-25"),
                ]
            }
        },
    )
    assert edgar._obtener_valor_instante("cik", ["StockholdersEquity"]) == 150


def test_obtener_valor_instante_none_si_dato_obsoleto(monkeypatch):
    monkeypatch.setattr(
        edgar,
        "_request",
        lambda url: {"units": {"USD": [_instante(100, "2013-06-30", "2013-07-25")]}},
    )
    assert edgar._obtener_valor_instante("cik", ["StockholdersEquity"]) is None


def test_obtener_deuda_patrimonio_calcula_el_ratio(monkeypatch):
    def _request_falso(url):
        if "StockholdersEquity" in url:
            return {"units": {"USD": [_instante(1000, "2026-06-30", "2026-07-25")]}}
        return {"units": {"USD": [_instante(200, "2026-06-30", "2026-07-25")]}}

    monkeypatch.setattr(edgar, "_request", _request_falso)
    assert edgar.obtener_deuda_patrimonio("cik") == 0.2


def test_obtener_deuda_patrimonio_none_sin_patrimonio(monkeypatch):
    monkeypatch.setattr(edgar, "_request", lambda url: {"units": {"USD": []}})
    assert edgar.obtener_deuda_patrimonio("cik") is None


def test_obtener_deuda_patrimonio_trata_deuda_ausente_como_cero(monkeypatch):
    def _request_falso(url):
        if "StockholdersEquity" in url:
            return {"units": {"USD": [_instante(1000, "2026-06-30", "2026-07-25")]}}
        raise edgar.EdgarError("404")

    monkeypatch.setattr(edgar, "_request", _request_falso)
    assert edgar.obtener_deuda_patrimonio("cik") == 0.0
