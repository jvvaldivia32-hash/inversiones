import datetime

import feedparser

from medios import resolver_medio

USER_AGENT = "Mozilla/5.0 (inversiones-recolector)"


def leer_feed(url: str, medio: str, dominio: str) -> list[dict]:
    """Lee un feed RSS/Atom y devuelve artículos con el shape del tipo Articulo del
    frontend. Nunca levanta excepción — un feed caído no debe tumbar el resto (mismo
    criterio que sources/prices.py). `extracto` queda vacío a propósito: sin Gemini no hay
    forma de reescribirlo, y la regla dura de copyright prohíbe copiar el original."""
    try:
        parsed = feedparser.parse(url, agent=USER_AGENT)
    except Exception:
        return []

    if not parsed.entries:
        return []

    info = resolver_medio(dominio, medio)
    articulos = []
    for entrada in parsed.entries:
        titular = entrada.get("title", "").strip()
        link = entrada.get("link", "").strip()
        if not titular or not link:
            continue
        articulos.append(
            {
                "titular": titular,
                "extracto": "",
                "medio": info["medio"],
                "grupo": info["grupo"],
                "lean": info["lean"],
                "url": link,
                "fecha": _fecha_iso(entrada),
            }
        )
    return articulos


def _fecha_iso(entrada) -> str:
    tupla = entrada.get("published_parsed") or entrada.get("updated_parsed")
    if tupla:
        return datetime.datetime(*tupla[:6], tzinfo=datetime.timezone.utc).isoformat()
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
