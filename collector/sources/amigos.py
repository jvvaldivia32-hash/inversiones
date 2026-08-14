"""Datos en vivo para la sección "Amigos" — extra fuera del plan madre (2026-08-14).
Cada amigo elige UNO de dos modos (tickers propios, o una palabra clave con mini recap de
noticias) desde su propio link, sin clave compartida (ver web/api/amigos.ts para el
límite: solo se puede editar un id que ya existe, nunca crear uno nuevo). Acá solo se
resuelven los datos en vivo — nada de esto llama a Gemini ni gasta cuota más allá de lo
que ya gasta cualquier ticker/feed normal del collector."""

import urllib.parse

from . import prices, rss

MAX_TICKERS_POR_AMIGO = 2
MAX_TITULARES_RECAP = 3
VENTANA_BUSQUEDA = "7d"


def obtener_datos_tickers(tickers: list[str]) -> list[dict]:
    """Precio y variación diaria por ticker (tope MAX_TICKERS_POR_AMIGO) — mismo cliente
    Finnhub que ya usa el resto del collector (sources/prices.py), sin agregar ninguna
    llamada nueva. Cada ticker degrada independiente: si uno falla, los demás igual
    salen."""
    resultado = []
    for ticker in tickers[:MAX_TICKERS_POR_AMIGO]:
        try:
            cot = prices.obtener_cotizacion(ticker)
            resultado.append(
                {"ticker": ticker, "precio": cot["precio"], "var_dia_pct": cot["var_dia_pct"]}
            )
        except prices.FinnhubError:
            continue
    return resultado


def obtener_recap_palabra_clave(palabra_clave: str) -> list[dict]:
    """Titulares crudos (sin extracto, sin Gemini) de Google News RSS para una palabra
    clave libre — mismo mecanismo que sources/feeds.py ya usa para el workaround de
    Reuters (site:reuters.com), acá con una búsqueda libre. No reescribe ni resume nada:
    "Amigos" es todavía más mini que Actualidad, que también muestra el titular tal cual
    viene del feed (regla dura de copyright: nunca copiar un extracto, y acá ni siquiera
    se intenta armar uno)."""
    if not palabra_clave:
        return []
    query = urllib.parse.quote(f"{palabra_clave} when:{VENTANA_BUSQUEDA}")
    url = f"https://news.google.com/rss/search?q={query}&hl=es-419&gl=CL&ceid=CL:es"
    articulos = rss.leer_feed(url, "Google News", "news.google.com")
    return [
        {"titular": a["titular"], "medio": a["medio"], "url": a["url"]}
        for a in articulos[:MAX_TITULARES_RECAP]
    ]
