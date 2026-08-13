import json
import os
import urllib.error
import urllib.request

BASE_URL = "https://data.sec.gov"

# CIKs verificados a mano contra SEC EDGAR (10 dígitos con ceros a la izquierda — formato
# que exige companyconcept). VOO es un ETF: no presenta 10-Q/10-K, por diseño no está acá.
CIK_POR_TICKER = {
    "AAPL": "0000320193",
    "BRK.B": "0001067983",
    "MCD": "0000063908",
    "MSFT": "0000789019",
}

# Tag `us-gaap`, unidad XBRL y divisor para llegar a la unidad que espera el visor
# (Fundamentales.series en web/src/types.ts) — sección 2.3 del plan madre.
TAGS = {
    "ingresos_musd": ("RevenueFromContractWithCustomerExcludingAssessedTax", "USD", 1_000_000),
    "op_income_musd": ("OperatingIncomeLoss", "USD", 1_000_000),
    "eps_gaap": ("EarningsPerShareDiluted", "USD/shares", 1),
    "capex_musd": ("PaymentsToAcquirePropertyPlantAndEquipment", "USD", 1_000_000),
    "flujo_op_musd": ("NetCashProvidedByUsedInOperatingActivities", "USD", 1_000_000),
}

# eps_non_gaap NO está acá a propósito: no es un tag XBRL estándar (es una métrica que
# cada empresa define en prosa dentro de su press release) — le toca a Fase 5 vía Gemini,
# no a esta extracción XBRL. Ver nota al usuario.

FORMULARIOS_TRIMESTRALES = {"10-Q", "10-K"}
FASES_TRIMESTRE = {"Q1", "Q2", "Q3", "Q4"}
TRIMESTRES = 12


class EdgarError(Exception):
    pass


def _headers() -> dict:
    user_agent = os.environ.get("SEC_USER_AGENT")
    if not user_agent:
        raise EdgarError("SEC_USER_AGENT no está seteada")
    return {"User-Agent": user_agent}


def _request(url: str) -> dict:
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise EdgarError(f"EDGAR {url} respondió {e.code}") from e
    except urllib.error.URLError as e:
        raise EdgarError(f"EDGAR {url} no respondió: {e.reason}") from e


def _ultimo_accession(cik: str) -> str | None:
    """Accession number del filing 10-Q/10-K más reciente. Se usa como llave de cache:
    si no cambió desde la corrida anterior, no vale la pena repegarle a los 5 tags de
    companyconcept — los fundamentales cambian ~4 veces al año, no cada hora."""
    data = _request(f"{BASE_URL}/submissions/CIK{cik}.json")
    recientes = data.get("filings", {}).get("recent", {})
    formularios = recientes.get("form", [])
    accesiones = recientes.get("accessionNumber", [])
    for forma, accn in zip(formularios, accesiones):
        if forma in FORMULARIOS_TRIMESTRALES:
            return accn
    return None


def _periodo(fy: int, fp: str) -> str:
    return f"FY{fy % 100:02d}{fp}"


def _extraer_serie(data: dict, unidad: str, divisor: int) -> list[dict]:
    puntos = data.get("units", {}).get(unidad, [])
    candidatos = [
        p
        for p in puntos
        if p.get("form") in FORMULARIOS_TRIMESTRALES and p.get("fp") in FASES_TRIMESTRE
    ]

    # Un mismo trimestre puede aparecer más de una vez (el 10-K reafirma los comparativos
    # del último Q del año anterior) — se queda con el filing más reciente (`filed`).
    por_periodo: dict[str, dict] = {}
    for p in candidatos:
        clave = _periodo(p["fy"], p["fp"])
        actual = por_periodo.get(clave)
        if actual is None or p["filed"] > actual["filed"]:
            por_periodo[clave] = p

    ordenados = sorted(por_periodo.items(), key=lambda kv: kv[1]["end"])
    return [
        {"periodo": clave, "valor": p["val"] / divisor} for clave, p in ordenados[-TRIMESTRES:]
    ]


def _derivar_margen(ingresos: list[dict], op_income: list[dict]) -> list[dict]:
    ing_por_periodo = {p["periodo"]: p["valor"] for p in ingresos}
    resultado = []
    for punto in op_income:
        ing = ing_por_periodo.get(punto["periodo"])
        if ing:
            resultado.append({"periodo": punto["periodo"], "valor": punto["valor"] / ing * 100})
    return resultado


def _fuente_url(cik: str, accession: str) -> str:
    cik_sin_ceros = str(int(cik))
    accn_sin_guiones = accession.replace("-", "")
    return (
        f"https://www.sec.gov/Archives/edgar/data/{cik_sin_ceros}/{accn_sin_guiones}/"
        f"{accession}-index.htm"
    )


def obtener_fundamentales(ticker: str, accession_anterior: str | None) -> dict | None:
    """Fundamentales reales desde SEC EDGAR, o None si el ticker no tiene CIK conocido o
    el último filing es el mismo que la corrida anterior (nada que actualizar). Quien
    llama decide si conserva el valor previo — mismo criterio de degradación que
    sources/banco_central.py."""
    cik = CIK_POR_TICKER.get(ticker)
    if cik is None:
        return None

    accession = _ultimo_accession(cik)
    if accession is None or accession == accession_anterior:
        return None

    series = {}
    for campo, (tag, unidad, divisor) in TAGS.items():
        data = _request(f"{BASE_URL}/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json")
        series[campo] = _extraer_serie(data, unidad, divisor)

    series["margen_operativo"] = _derivar_margen(series["ingresos_musd"], series["op_income_musd"])
    series["eps_non_gaap"] = []  # no viene de XBRL — pendiente Fase 5 (press release + Gemini)

    if not series["ingresos_musd"]:
        raise EdgarError(f"{ticker}: companyconcept no devolvió ingresos trimestrales")

    return {
        "periodo": series["ingresos_musd"][-1]["periodo"],
        "fuente_url": _fuente_url(cik, accession),
        "series": series,
        "_accession": accession,
    }
