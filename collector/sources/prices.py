import datetime
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://finnhub.io/api/v1"


class FinnhubError(Exception):
    pass


def _request(ruta: str, params: dict) -> dict:
    token = os.environ.get("FINNHUB_KEY")
    if not token:
        raise FinnhubError("FINNHUB_KEY no está seteada")
    url = f"{BASE_URL}{ruta}?{urllib.parse.urlencode({**params, 'token': token})}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise FinnhubError(f"Finnhub {ruta} respondió {e.code}") from e
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        # TimeoutError no es subclase de URLError (viene de socket, no de urllib) — mismo
        # gotcha ya visto y arreglado en sources/gemini.py.
        raise FinnhubError(f"Finnhub {ruta} no respondió: {e}") from e


def obtener_cotizacion(ticker: str) -> dict:
    """Precio actual y variación del día — endpoint `quote`."""
    data = _request("/quote", {"symbol": ticker})
    if not data.get("c") and not data.get("pc"):
        raise FinnhubError(f"Sin datos de cotización para {ticker}")
    return {
        "precio": data["c"],
        "var_dia_pct": data.get("dp"),
        "cierre_anterior": data.get("pc"),
    }


def obtener_velas(ticker: str, dias: int) -> list[dict]:
    """Histórico diario de cierre para el gráfico — endpoint `stock/candle`.

    Devuelve lista vacía si Finnhub no tiene datos (ticker sin historial en el rango,
    plan free sin cobertura, etc.) en vez de fallar — el gráfico simplemente no se pinta
    para ese rango, no tumba el resto del recolector.
    """
    ahora = int(time.time())
    desde = ahora - dias * 24 * 60 * 60
    data = _request(
        "/stock/candle",
        {"symbol": ticker, "resolution": "D", "from": desde, "to": ahora},
    )
    if data.get("s") != "ok":
        return []
    return [
        {"fecha": _timestamp_a_fecha(t), "valor": c}
        for t, c in zip(data["t"], data["c"])
    ]


def _timestamp_a_fecha(ts: int) -> str:
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
