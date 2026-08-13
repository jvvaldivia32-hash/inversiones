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


def _punto(fy, fp, val, filed, end, form="10-Q"):
    return {"fy": fy, "fp": fp, "val": val, "filed": filed, "end": end, "form": form}


def test_extraer_serie_ordena_y_recorta_a_12_trimestres():
    puntos = [_punto(2025, f"Q{n}", 100 + n, "2025-01-01", f"2025-0{n}-30") for n in range(1, 5)]
    puntos += [_punto(2026, f"Q{n}", 200 + n, "2026-01-01", f"2026-0{n}-30") for n in range(1, 5)]
    data = {"units": {"USD": puntos}}
    serie = edgar._extraer_serie(data, "USD", 1)
    assert [p["periodo"] for p in serie] == [
        "FY25Q1", "FY25Q2", "FY25Q3", "FY25Q4",
        "FY26Q1", "FY26Q2", "FY26Q3", "FY26Q4",
    ]
    assert serie[-1]["valor"] == 204


def test_extraer_serie_se_queda_con_el_filing_mas_reciente_por_periodo():
    puntos = [
        _punto(2026, "Q4", 100, filed="2026-01-10", end="2025-12-31", form="10-K"),
        _punto(2026, "Q4", 999, filed="2026-04-01", end="2025-12-31", form="10-K"),
    ]
    data = {"units": {"USD": puntos}}
    serie = edgar._extraer_serie(data, "USD", 1)
    assert len(serie) == 1
    assert serie[0]["valor"] == 999


def test_extraer_serie_ignora_form_no_trimestral():
    puntos = [_punto(2026, "Q1", 500, "2026-01-10", "2026-03-31", form="8-K")]
    data = {"units": {"USD": puntos}}
    assert edgar._extraer_serie(data, "USD", 1) == []


def test_extraer_serie_convierte_a_millones():
    puntos = [_punto(2026, "Q1", 75_800_000_000, "2026-04-25", "2026-03-31")]
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


def test_obtener_fundamentales_ticker_sin_cik_devuelve_none():
    assert edgar.obtener_fundamentales("VOO", None) is None


def test_obtener_fundamentales_sin_cambios_devuelve_none(monkeypatch):
    monkeypatch.setattr(edgar, "_ultimo_accession", lambda cik: "misma-accession")
    assert edgar.obtener_fundamentales("MSFT", "misma-accession") is None


def test_obtener_fundamentales_arma_el_shape_completo(monkeypatch):
    monkeypatch.setattr(edgar, "_ultimo_accession", lambda cik: "0000789019-26-000042")

    def _request_falso(url):
        if "ingresos" in url or "RevenueFromContract" in url:
            return {"units": {"USD": [_punto(2026, "Q4", 90_007_000_000, "2026-07-25", "2026-06-30", "10-K")]}}
        if "OperatingIncomeLoss" in url:
            return {"units": {"USD": [_punto(2026, "Q4", 40_603_000_000, "2026-07-25", "2026-06-30", "10-K")]}}
        if "EarningsPerShareDiluted" in url:
            return {"units": {"USD/shares": [_punto(2026, "Q4", 4.81, "2026-07-25", "2026-06-30", "10-K")]}}
        return {"units": {"USD": [_punto(2026, "Q4", 1_000_000, "2026-07-25", "2026-06-30", "10-K")]}}

    monkeypatch.setattr(edgar, "_request", _request_falso)

    resultado = edgar.obtener_fundamentales("MSFT", None)
    assert resultado["periodo"] == "FY26Q4"
    assert resultado["_accession"] == "0000789019-26-000042"
    assert resultado["series"]["ingresos_musd"][0]["valor"] == 90007.0
    assert resultado["series"]["eps_gaap"][0]["valor"] == 4.81
    assert resultado["series"]["eps_non_gaap"] == []
    assert round(resultado["series"]["margen_operativo"][0]["valor"], 1) == 45.1
    assert "sec.gov" in resultado["fuente_url"]
