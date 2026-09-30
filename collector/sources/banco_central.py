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
    # Sumados 2026-09-30 (pedido del usuario). PIB: volumen a precios del año anterior
    # encadenado, referencia 2018, en miles de millones de pesos — no es un índice ni un
    # % de variación, es el nivel trimestral tal cual lo publica el Banco Central.
    "pib": "F032.PIB.FLU.R.CLP.EP18.Z.Z.0.T",
    # Desocupación: tasa nacional, no ajustada por estacionalidad (INE, Encuesta Nacional
    # de Empleo) — es la cifra que se cita como titular en la prensa, no la desestacionalizada.
    "desocupacion": "F049.DES.TAS.INE9.10.M",
}

# `dias` de ventana por campo — el default (45) alcanza para series diarias/mensuales de
# publicación rápida (ver docstring de _obtener_valor), pero la desocupación la publica el
# INE con ~2 meses de rezago sobre la fecha de hoy. Encontrado de verdad corriendo contra la
# API real: con 45 días `desocupacion` volvía vacío en silencio, mismo síntoma que ya había
# pasado con IPC/IPSA. El PIB (trimestral) usa su propia ventana en _pib().
DIAS_POR_CAMPO = {"desocupacion": 120}


class BancoCentralError(Exception):
    pass


def _obtener_observaciones(codigo: str, dias: int) -> list[tuple[datetime.date, float]]:
    """Observaciones "OK" de la serie en los últimos `dias`, de la más vieja a la más
    nueva. La API marca los días sin dato (fines de semana, feriados) con statusCode "ND" —
    esos se saltan. Lista vacía si falla (no levanta excepción — mismo criterio de
    degradación que sources/prices.py)."""
    token = os.environ.get("BCCH_API_KEY")
    if not token:
        return []

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
    # OSError y no solo URLError: un timeout a mitad de la *lectura* llega como
    # TimeoutError pelado, no envuelto en URLError — la misma trampa que en Fase 6 tumbó
    # corridas enteras en yahoo.py/edgar.py/prices.py. main.py no envuelve esta llamada.
    except (OSError, json.JSONDecodeError):
        return []

    if data.get("Codigo") != 0:
        return []

    salida = []
    for obs in data.get("Series", {}).get("Obs") or []:
        if obs.get("statusCode") != "OK":
            continue
        try:
            fecha = datetime.datetime.strptime(obs["indexDateString"], "%d-%m-%Y").date()
            salida.append((fecha, float(obs["value"])))
        except (KeyError, ValueError):
            continue
    return salida


def _obtener_valor(codigo: str, dias: int = 45) -> float | None:
    """Último valor disponible de una serie, o None.

    `dias=45` por defecto: series diarias (UF, dólar, TPM) no lo necesitan, pero las
    mensuales (IPSA, IPC) publican una sola observación al mes — con una ventana más chica
    (probado con 10 días) la última observación puede quedar fuera del rango y esto
    devuelve None en silencio, sin ningún error visible. Ya pasó de verdad en una corrida
    real: IPSA e IPC volvían el valor inventado de Fase 0 en vez de fallar audiblemente."""
    obs = _obtener_observaciones(codigo, dias)
    return obs[-1][1] if obs else None


_MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _periodo_trimestre(fecha: datetime.date) -> str:
    """"01-04-2026" (así fecha el Banco Central un trimestre) → "T2 2026"."""
    return f"T{(fecha.month - 1) // 3 + 1} {fecha.year}"


def _periodo_trimestre_movil(fecha: datetime.date) -> str:
    """La desocupación del INE es un trimestre móvil que *termina* en el mes de la fecha:
    "01-07-2026" → "may–jul 2026". Verificado contra los boletines del INE (el 8,33% de
    "01-02-2026" es el "8,3% dic 2025–feb 2026" que publicó el INE)."""
    inicio = _MESES[(fecha.month - 3) % 12]
    return f"{inicio}–{_MESES[fecha.month - 1]} {fecha.year}"


def _pib() -> dict:
    """Nivel del último trimestre, su variación contra el *mismo trimestre del año
    anterior* y el período. Anual y no contra el trimestre previo porque la serie es la
    original, sin desestacionalizar: comparar T2 contra T1 mezclaría estacionalidad con
    crecimiento. Es la misma cifra que titula el Banco Central (T2 2026: −0,2%, calzó con el
    cálculo de acá). 500 días de ventana para alcanzar a tener el trimestre de hace un año."""
    obs = _obtener_observaciones(SERIES["pib"], 500)
    if not obs:
        return {}
    fecha, valor = obs[-1]
    salida = {"pib": valor, "pib_periodo": _periodo_trimestre(fecha)}
    hace_un_anio = dict(obs).get(fecha.replace(year=fecha.year - 1))
    if hace_un_anio:
        salida["pib_var_12m"] = (valor / hace_un_anio - 1) * 100
    return salida


def obtener_referencias_chile() -> dict:
    """Shape exacto de ReferenciasChile en web/src/types.ts. Los campos que no se pudieron
    obtener quedan fuera del diccionario (no se rellenan con None) — quien llama decide si
    conserva el valor anterior."""
    resultado = {"fuente": "Banco Central de Chile"}
    for campo, codigo in SERIES.items():
        if campo == "pib":
            resultado.update(_pib())
            continue
        if campo == "desocupacion":
            obs = _obtener_observaciones(codigo, DIAS_POR_CAMPO["desocupacion"])
            if obs:
                resultado["desocupacion"] = obs[-1][1]
                resultado["desocupacion_periodo"] = _periodo_trimestre_movil(obs[-1][0])
            continue
        valor = _obtener_valor(codigo, dias=DIAS_POR_CAMPO.get(campo, 45))
        if valor is not None:
            resultado[campo] = valor
    return resultado
