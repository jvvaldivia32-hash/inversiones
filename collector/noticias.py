from sources import feeds, rss

# Cuántas "historias" como máximo por bloque — sin esto, sumar varios feeds da cientos de
# artículos (probado: 314 en mundo, 86 en chile en una corrida real), que es justo lo
# opuesto al "instrumento de lectura, no terminal de trading" del plan madre.
MUNDO_MAX = 8
CHILE_MAX = 8

# Heurística de palabras clave para separar Mundo (económico/serio) de Actualidad (todo lo
# demás) — sin Gemini todavía no hay forma más fina de clasificar. Es un fallback a
# propósito, mismo espíritu que el fallback sin LLM que ya anticipa el plan madre para la
# agrupación ("peor, pero funciona").
PALABRAS_ECONOMIA = [
    "fed",
    "inflación",
    "inflation",
    "mercado",
    "market",
    "dólar",
    "dollar",
    "tasa de interés",
    "interest rate",
    "pib",
    "gdp",
    "banco central",
    "central bank",
    "comercio",
    "trade",
    "acciones",
    "stocks",
    "bolsa",
    "economía",
    "economy",
    "arancel",
    "tariff",
    "recesión",
    "recession",
]


def _es_economico(titular: str) -> bool:
    titular_min = titular.lower()
    return any(palabra in titular_min for palabra in PALABRAS_ECONOMIA)


def _envolver_historia(articulo: dict) -> dict:
    """Fase 2 no agrupa todavía (eso es Fase 3, necesita Gemini) — cada artículo queda
    como su propia 'historia' de una sola fuente. cobertura_unilateral=True es honesto:
    literalmente hay una sola fuente hasta que exista agrupación real."""
    return {
        "titulo_neutral": articulo["titular"],
        "resumen": "",
        "articulos": [articulo],
        "leans_presentes": [articulo["lean"]],
        "grupos_presentes": [articulo["grupo"]],
        "cobertura_unilateral": True,
    }


def recolectar_bloques() -> tuple[list[dict], list[dict], list[dict], list[str]]:
    """Devuelve (mundo, chile, actualidad, errores)."""
    vistos: set[str] = set()
    errores: list[str] = []

    def leer_todos(catalogo):
        articulos = []
        for url, medio, dominio in catalogo:
            resultado = rss.leer_feed(url, medio, dominio)
            if not resultado:
                errores.append(f"{medio}: feed sin respuesta o vacío")
                continue
            for a in resultado:
                if a["url"] in vistos:
                    continue
                vistos.add(a["url"])
                articulos.append(a)
        return articulos

    articulos_mundo_crudo = leer_todos(feeds.FEEDS_MUNDO)
    articulos_chile = leer_todos(feeds.FEEDS_CHILE)

    mundo, actualidad_candidatos = [], []
    for a in articulos_mundo_crudo:
        (mundo if _es_economico(a["titular"]) else actualidad_candidatos).append(a)

    # Más reciente primero, y se recorta — sin esto un solo feed grande (BBC, Al Jazeera)
    # llena el bloque entero de puros items del mismo medio.
    mundo.sort(key=lambda a: a["fecha"], reverse=True)
    articulos_chile.sort(key=lambda a: a["fecha"], reverse=True)
    actualidad_candidatos.sort(key=lambda a: a["fecha"], reverse=True)

    bloque_mundo = [_envolver_historia(a) for a in mundo[:MUNDO_MAX]]
    bloque_chile = [_envolver_historia(a) for a in articulos_chile[:CHILE_MAX]]
    bloque_actualidad = [
        {"titular": a["titular"], "medio": a["medio"], "url": a["url"], "fecha": a["fecha"]}
        for a in actualidad_candidatos[:5]
    ]

    return bloque_mundo, bloque_chile, bloque_actualidad, errores


def noticias_ticker(ticker: str) -> list[dict]:
    articulos = rss.leer_feed(feeds.feed_noticias_ticker(ticker), "Yahoo Finance", "finance.yahoo.com")
    return articulos[:5]
