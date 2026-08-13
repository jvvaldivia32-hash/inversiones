import datetime
import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"

# Códigos verificados a mano contra la API real (con token real), no adivinados — ver
# docs/plan-app-inversiones.md sección 2.5 para el detalle de cómo se encontró cada uno.
SERIES = {
    "uf": "F073.UFF.PRE.Z.D",
    "dolar": "F073.TCO.PRE.Z.D",
    "tpm": "F022.TPM.TIN.D001.NO.Z.D",
    "ipc_12m": "G073.IPC.V12.2023.M",
    "ipsa": "F013.IBC.IND.N.7.LAC.CL.CLP.BLO.M",
}


class BancoCentralError(Exception):
    pass


def _obtener_valor(codigo: str, dias: int = 45) -> float | None:
    """Último valor disponible de una serie. La API a veces marca los días sin dato
    (fines de semana, feriados) con statusCode "ND" — se recorre desde el más reciente y
    se toma el primer "OK". Devuelve None si falla o no hay ningún valor "OK" en el rango
    (no levanta excepción — mismo criterio de degradación que sources/prices.py).

    `dias=45` por defecto: series diarias (UF, dólar, TPM) no lo necesitan, pero las
    mensuales (IPSA, IPC) publican una sola observación al mes — con una ventana más chica
    (probado con 10 días) la última observación puede quedar fuera del rango y esto
    devuelve None en silencio, sin ningún error visible. Ya pasó de verdad en una corrida
    real: IPSA e IPC volvían el valor inventado de Fase 0 en vez de fallar audiblemente."""
    token = os.environ.get("BCCH_API_KEY")
    if not token:
        return None

    hoy = datetime.date.today()
    desde = hoy - datetime.timedelta(days=dias)
    params = {
        "token": token,
        "function": "GetSeries",
        "timeseries": codigo,
        "firstdate": desde.isoformat(),
        "lastdate": hoy.isoformat(),
    }
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            # La API responde en latin-1, no utf-8 — confirmado contra el servicio real
            # (revienta con UnicodeDecodeError si se asume utf-8).
            data = json.loads(resp.read().decode("latin-1"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return None

    if data.get("Codigo") != 0:
        return None

    observaciones = data.get("Series", {}).get("Obs", [])
    for obs in reversed(observaciones):
        if obs.get("statusCode") == "OK":
            try:
                return float(obs["value"])
            except (KeyError, ValueError):
                continue
    return None


def obtener_referencias_chile() -> dict:
    """{"uf", "dolar", "tpm", "ipc_12m", "ipsa", "fuente"} — shape exacto de
    ReferenciasChile en web/src/types.ts. Los campos que no se pudieron obtener quedan
    fuera del diccionario (no se rellenan con None) — quien llama decide si conserva el
    valor anterior."""
    resultado = {"fuente": "Banco Central de Chile"}
    for campo, codigo in SERIES.items():
        valor = _obtener_valor(codigo)
        if valor is not None:
            resultado[campo] = valor
    return resultado
