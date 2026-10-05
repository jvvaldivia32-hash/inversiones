import datetime
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://finnhub.io/api/v1"

# Free tier: 60 llamadas/minuto. El Radar pide ~80 quotes seguidas y desde fines de agosto
# todo lo que pasaba del límite volvía 429 y el precio quedaba congelado (ORCL quieto en el
# del 24-08 hasta el 05-10, y el simulador mostrando 0% encima). Un 429 se espera y se
# reintenta en vez de darse por perdido.
ESPERA_429_S = 61
REINTENTOS_429 = 2


class FinnhubError(Exception):
    pass


def _request(ruta: str, params: dict) -> dict:
    token = os.environ.get("FINNHUB_KEY")
    if not token:
        raise FinnhubError("FINNHUB_KEY no está seteada")
    url = f"{BASE_URL}{ruta}?{urllib.parse.urlencode({**params, 'token': token})}"
    for intento in range(REINTENTOS_429 + 1):
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and intento < REINTENTOS_429:
                time.sleep(ESPERA_429_S)
                continue
            raise FinnhubError(f"Finnhub {ruta} respondió {e.code}") from e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            # TimeoutError no es subclase de URLError (viene de socket, no de urllib) — mismo
            # gotcha ya visto y arreglado en sources/gemini.py.
            raise FinnhubError(f"Finnhub {ruta} no respondió: {e}") from e
    raise AssertionError("inalcanzable")


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


# finnhubIndustry viene en inglés; lo que no esté acá se muestra tal cual.
SECTORES_ES = {
    "Technology": "Tecnología",
    "Media": "Medios",
    "Financial Services": "Servicios financieros",
    "Banking": "Bancos",
    "Insurance": "Seguros",
    "Automobiles": "Automotriz",
    "Hotels, Restaurants & Leisure": "Restaurantes y ocio",
    "Retail": "Retail",
    "Beverages": "Bebidas",
    "Food Products": "Alimentos",
    "Pharmaceuticals": "Farmacéuticas",
    "Biotechnology": "Biotecnología",
    "Health Care": "Salud",
    "Semiconductors": "Semiconductores",
    "Utilities": "Servicios básicos",
    "Energy": "Energía",
    "Aerospace & Defense": "Aeroespacial y defensa",
    "Machinery": "Maquinaria",
    "Industrial Conglomerates": "Conglomerados industriales",
    "Logistics & Transportation": "Logística y transporte",
    "Telecommunication": "Telecomunicaciones",
    "Real Estate": "Inmobiliario",
    "Chemicals": "Químicos",
    "Consumer products": "Consumo",
}


def obtener_sector(ticker: str) -> str | None:
    """Industria según Finnhub (endpoint `stock/profile2`, free tier). None si Finnhub no
    tiene perfil — pasa con los ETF (VOO, QQQ)."""
    industria = _request("/stock/profile2", {"symbol": ticker}).get("finnhubIndustry")
    if not industria:
        return None
    return SECTORES_ES.get(industria, industria)


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
