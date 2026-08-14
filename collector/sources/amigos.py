"""Datos en vivo para la sección "Amigos" — extra fuera del plan madre (2026-08-14).

Cada amigo arma su propia mini lista de "seguimientos" (mezcla libre de tickers propios y
palabras clave, hasta un tope) desde su propio link, sin clave compartida (ver
web/api/amigos.ts para el límite real: solo se puede editar un id que ya existe, nunca
crear uno nuevo). Acá solo se resuelven los datos en vivo de cada seguimiento — nada de
esto llama a Gemini ni gasta cuota más allá de lo que ya gasta cualquier ticker/feed
normal del collector."""

import urllib.parse

from . import prices, rss

MAX_SEGUIMIENTOS = 4
MAX_TICKERS_POR_AMIGO = 2  # de los MAX_SEGUIMIENTOS, cuántos como máximo pueden ser tickers
MAX_TITULARES_RECAP = 3
VENTANA_BUSQUEDA = "7d"


def obtener_dato_ticker(ticker: str) -> dict | None:
    """Precio y variación diaria de un ticker — mismo cliente Finnhub que ya usa el resto
    del collector (sources/prices.py), sin agregar ninguna llamada nueva. None si
    Finnhub no responde para ese ticker puntual (no tumba los demás seguimientos)."""
    try:
        cot = prices.obtener_cotizacion(ticker)
        return {"precio": cot["precio"], "var_dia_pct": cot["var_dia_pct"]}
    except prices.FinnhubError:
        return None


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
