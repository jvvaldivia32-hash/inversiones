import datetime
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

# Tag(s) `us-gaap`, unidad XBRL y divisor para llegar a la unidad que espera el visor
# (Fundamentales.series en web/src/types.ts) — sección 2.3 del plan madre. Más de un tag
# candidato por campo: no todas las empresas usan el mismo tag para "lo mismo" (MCD
# taguea ingresos como `Revenues`, MSFT/AAPL como `RevenueFromContractWith...` — probado
# a mano contra ambos CIKs) — se prueba en orden y se usa el primero que responda.
TAGS = {
    "ingresos_musd": (
        ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
        "USD",
        1_000_000,
    ),
    "op_income_musd": (["OperatingIncomeLoss"], "USD", 1_000_000),
    # BRK.B solo taguea EarningsPerShareBasic (probado a mano) — si cae al fallback, lo
    # que se muestra como "EPS diluido" es en realidad EPS básico para ese ticker
    # puntual. Sin distinción visual todavía; ver nota al usuario.
    "eps_gaap": (["EarningsPerShareDiluted", "EarningsPerShareBasic"], "USD/shares", 1),
    "capex_musd": (["PaymentsToAcquirePropertyPlantAndEquipment"], "USD", 1_000_000),
    "flujo_op_musd": (["NetCashProvidedByUsedInOperatingActivities"], "USD", 1_000_000),
}

# eps_non_gaap NO está acá a propósito: no es un tag XBRL estándar (es una métrica que
# cada empresa define en prosa dentro de su press release) — le toca a Fase 5 vía Gemini,
# no a esta extracción XBRL. Ver nota al usuario.

FORMULARIOS_TRIMESTRALES = {"10-Q", "10-K"}
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


def request_texto(url: str) -> str:
    """Como _request pero para documentos que no son JSON (los exhibits de un 8-K son
    HTML) — mismo header, mismos errores. Público porque sources/segmentos.py también
    lo necesita para bajar el press release."""
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise EdgarError(f"EDGAR {url} respondió {e.code}") from e
    except urllib.error.URLError as e:
        raise EdgarError(f"EDGAR {url} no respondió: {e.reason}") from e


def _tiene_datos_recientes(data: dict, dias_maximos: int = 550) -> bool:
    """Un tag puede existir y responder 200 sin tener nada útil: la empresa lo usó hace
    años y después migró a otro (o dejó de tagearlo del todo, como el EPS de BRK.B).
    550 días cubre un año fiscal + margen para el filing más lento."""
    limite = datetime.date.today() - datetime.timedelta(days=dias_maximos)
    for puntos in data.get("units", {}).values():
        for p in puntos:
            filed = p.get("filed")
            if filed and datetime.date.fromisoformat(filed) >= limite:
                return True
    return False


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


def _duracion_dias(punto: dict) -> int:
    ini = datetime.date.fromisoformat(punto["start"])
    fin = datetime.date.fromisoformat(punto["end"])
    return (fin - ini).days


def _extraer_serie(data: dict, unidad: str, divisor: int) -> list[dict]:
    """XBRL no trae el trimestre discreto servido en bandeja: cada 10-Q tagea el
    acumulado year-to-date (a veces también el trimestre solo, a veces no), y el 10-K
    solo tagea el año fiscal completo — nunca un "Q4" explícito. Hay que separar por
    duración real (`end` - `start`) y, cuando no hay un hecho puntual de ~90 días para
    un período, derivarlo restando el checkpoint acumulado anterior dentro del mismo año
    fiscal (mismo `start`). Así sale Q4 = año completo (10-K) menos los primeros 9 meses
    (10-Q), que es como cualquier lector de estos filings lo calcularía a mano.

    Un mismo período (mismo start/end) suele reaparecer en 1-2 filings posteriores como
    comparativo — mismo valor, pero con un `fy` que en la práctica quedó pegado al año
    del filing que lo repite, no al año real del período. Por eso la ETIQUETA (fy/fp)
    sale del duplicado más antiguo (el filing donde ese período era "el actual"), y el
    VALOR del más reciente (por si hubo una restitución contable real entremedio)."""
    crudos = [
        p
        for p in data.get("units", {}).get(unidad, [])
        if p.get("form") in FORMULARIOS_TRIMESTRALES and p.get("start") and p.get("end")
    ]

    grupos: dict[tuple[str, str], dict] = {}
    for p in crudos:
        dias = _duracion_dias(p)
        if dias < 75:
            continue
        clave = (p["start"], p["end"])
        g = grupos.setdefault(clave, {"valor": p, "etiqueta": p, "dias": dias})
        if p["filed"] > g["valor"]["filed"]:
            g["valor"] = p
        if p["filed"] < g["etiqueta"]["filed"]:
            g["etiqueta"] = p

    puntuales = [g for g in grupos.values() if g["dias"] <= 100]

    acumulados: dict[str, list[dict]] = {}
    for (inicio, _fin), g in grupos.items():
        if g["dias"] > 100:
            acumulados.setdefault(inicio, []).append(g)
    for lista in acumulados.values():
        lista.sort(key=lambda g: g["etiqueta"]["end"])

    resultado: dict[str, dict] = {}

    for g in puntuales:
        clave = _periodo(g["etiqueta"]["fy"], g["etiqueta"]["fp"])
        resultado[clave] = {"periodo": clave, "valor": g["valor"]["val"] / divisor}

    for lista in acumulados.values():
        for i, g in enumerate(lista):
            fp = "Q4" if g["etiqueta"]["fp"] == "FY" else g["etiqueta"]["fp"]
            clave = _periodo(g["etiqueta"]["fy"], fp)
            if clave in resultado:
                continue
            anterior = lista[i - 1]["valor"]["val"] if i > 0 else 0
            resultado[clave] = {"periodo": clave, "valor": (g["valor"]["val"] - anterior) / divisor}

    ordenados = sorted(resultado.values(), key=lambda p: p["periodo"])
    return [{"periodo": p["periodo"], "valor": p["valor"]} for p in ordenados[-TRIMESTRES:]]


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
    for campo, (tags_candidatos, unidad, divisor) in TAGS.items():
        data = None
        for tag in tags_candidatos:
            try:
                candidato = _request(f"{BASE_URL}/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json")
            except EdgarError:
                continue
            if _tiene_datos_recientes(candidato):
                data = candidato
                break
        # Sin candidato con datos recientes (ninguno respondió, o el único tag que la
        # empresa usa lleva años sin actualizarse — BRK.B no taguea EPS en XBRL desde
        # 2013) el campo queda vacío, no rompe el fetch del ticker entero.
        series[campo] = _extraer_serie(data, unidad, divisor) if data is not None else []

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
