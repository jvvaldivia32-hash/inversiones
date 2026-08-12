import datetime
import json
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
USER_AGENT = "Mozilla/5.0"  # Yahoo rechaza requests sin User-Agent de navegador


def _simbolo_yahoo(ticker: str) -> str:
    # Igual que Stooq: clases de acción van con guion, no punto (BRK.B -> BRK-B)
    return ticker.replace(".", "-")


def _rango_para(dias: int) -> str:
    if dias <= 30:
        return "1mo"
    if dias <= 180:
        return "6mo"
    if dias <= 365:
        return "1y"
    return "5y"


def descargar_historico(ticker: str, dias: int = 1825) -> list[dict]:
    """Histórico diario de cierre vía el endpoint no oficial de gráficos de Yahoo Finance
    — la misma fuente que usa la librería yfinance. Sin key, sin registro. Se usa **solo**
    para sembrar un ticker que todavía no tiene ninguna entrada en historico_precios.json;
    nunca en la corrida horaria de siempre. Es un endpoint no documentado y puede cambiar o
    bloquearse sin aviso — por eso el radio de impacto se mantiene acotado a "sembrar una
    vez", igual que se evaluó (y descartó, por bot-wall) para Stooq.

    Devuelve lista vacía si algo falla, nunca levanta excepción — mismo criterio de
    degradación que el resto de sources/.
    """
    url = f"{BASE_URL}/{urllib.parse.quote(_simbolo_yahoo(ticker))}?range={_rango_para(dias)}&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError):
        return []

    try:
        resultado = data["chart"]["result"][0]
        timestamps = resultado["timestamp"]
        cierres = resultado["indicators"]["quote"][0]["close"]
    except (KeyError, IndexError, TypeError):
        return []

    limite = datetime.date.today() - datetime.timedelta(days=dias)
    puntos = []
    for ts, cierre in zip(timestamps, cierres):
        if cierre is None:
            continue
        fecha = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).date()
        if fecha < limite:
            continue
        puntos.append({"fecha": fecha.isoformat(), "valor": round(cierre, 2)})

    puntos.sort(key=lambda p: p["fecha"])
    return puntos
