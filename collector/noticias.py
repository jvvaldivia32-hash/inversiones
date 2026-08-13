import re

from sources import feeds, gemini, rss

# Cuántas "historias" como máximo por bloque — sin esto, sumar varios feeds da cientos de
# artículos (probado: 314 en mundo, 86 en chile en una corrida real), que es justo lo
# opuesto al "instrumento de lectura, no terminal de trading" del plan madre.
MUNDO_MAX = 8
CHILE_MAX = 8

# Cuántos artículos crudos como máximo se le pasan al agrupador (Gemini o keywords) antes de
# recortar a MUNDO_MAX/CHILE_MAX historias — más ancho que el tope final para no desperdiciar
# cupos en historias que la agrupación iba a fusionar.
POOL_MAX = 25

_PALABRA_CAPITALIZADA = re.compile(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}\b")

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
    # Encontrado en vivo (2026-08-13): "Anthropic's anticipated $2tn IPO" no matcheaba
    # ninguna palabra de la lista original — cayó a Actualidad (tope 5) en vez de Mundo
    # (tope 8) y se perdió por volumen. "ipo" faltaba directamente.
    "ipo",
    "oferta pública inicial",
    "valoración",
    "valuation",
]


def _es_economico(titular: str) -> bool:
    titular_min = titular.lower()
    return any(palabra in titular_min for palabra in PALABRAS_ECONOMIA)


def _articulo_publico(articulo: dict) -> dict:
    """Saca los campos de uso interno (prefijo `_`, ej. `_snippet_original`) antes de
    escribir a daily.json — no son parte del tipo Articulo del frontend."""
    return {k: v for k, v in articulo.items() if not k.startswith("_")}


def _sustantivos_propios(titular: str) -> set[str]:
    return set(_PALABRA_CAPITALIZADA.findall(titular))


def _agrupar_por_keywords(articulos: list[dict]) -> list[tuple[str, list[int]]]:
    """Fallback sin Gemini (sin key o si la llamada falla): agrupa por solapamiento de ≥2
    palabras capitalizadas en el titular (proxy de sustantivo propio) — el fallback "peor
    pero funciona" que ya anticipa el plan madre para la agrupación."""
    grupos: list[tuple[set[str], list[int]]] = []
    for i, a in enumerate(articulos):
        propios = _sustantivos_propios(a["titular"])
        destino = next((g for g in grupos if len(propios & g[0]) >= 2), None)
        if destino:
            destino[0].update(propios)
            destino[1].append(i)
        else:
            grupos.append((propios, [i]))
    return [(articulos[indices[0]]["titular"], indices) for _, indices in grupos]


def _construir_historia(
    titulo: str, indices: list[int], pool: list[dict], resumen: str | None
) -> dict:
    articulos_grupo = [pool[i] for i in indices]
    leans, grupos = [], []
    for a in articulos_grupo:
        if a["lean"] not in leans:
            leans.append(a["lean"])
        if a["grupo"] not in grupos:
            grupos.append(a["grupo"])
    return {
        "titulo_neutral": titulo,
        "resumen": resumen or "",
        "articulos": [_articulo_publico(a) for a in articulos_grupo],
        "leans_presentes": leans,
        "grupos_presentes": grupos,
        "cobertura_unilateral": len(grupos) <= 1,
    }


def _construir_bloque(articulos_crudos: list[dict], tope: int) -> list[dict]:
    """Agrupa (Gemini si hay key y responde bien, si no por keywords), reescribe un resumen
    por grupo, y recorta a `tope` historias — recién después de agrupar, no antes."""
    pool = articulos_crudos[:POOL_MAX]
    if not pool:
        return []

    titulares = [a["titular"] for a in pool]
    grupos = gemini.agrupar_historias(titulares)
    if grupos is None:
        grupos = _agrupar_por_keywords(pool)

    snippets_por_grupo = [
        " ".join(pool[i].get("_snippet_original", "") for i in indices).strip()
        for _, indices in grupos
    ]
    resumenes = gemini.reescribir_resumenes(snippets_por_grupo)
    if resumenes is None:
        resumenes = [None] * len(grupos)

    historias_con_fecha = []
    for (titulo, indices), resumen in zip(grupos, resumenes):
        fecha_mas_reciente = max(pool[i]["fecha"] for i in indices)
        historia = _construir_historia(titulo, indices, pool, resumen)
        historias_con_fecha.append((fecha_mas_reciente, historia))

    historias_con_fecha.sort(key=lambda par: par[0], reverse=True)
    return [historia for _, historia in historias_con_fecha[:tope]]


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

    bloque_mundo = _construir_bloque(mundo, MUNDO_MAX)
    bloque_chile = _construir_bloque(articulos_chile, CHILE_MAX)
    bloque_actualidad = [
        {"titular": a["titular"], "medio": a["medio"], "url": a["url"], "fecha": a["fecha"]}
        for a in actualidad_candidatos[:5]
    ]

    return bloque_mundo, bloque_chile, bloque_actualidad, errores


def noticias_ticker(ticker: str) -> list[dict]:
    articulos = rss.leer_feed(
        feeds.feed_noticias_ticker(ticker), "Yahoo Finance", "finance.yahoo.com"
    )[:5]
    if not articulos:
        return []

    snippets = [a.get("_snippet_original", "") for a in articulos]
    extractos = gemini.reescribir_resumenes(snippets)
    if extractos is None:
        extractos = [None] * len(articulos)

    salida = []
    for articulo, extracto in zip(articulos, extractos):
        publico = _articulo_publico(articulo)
        publico["extracto"] = extracto or ""
        salida.append(publico)
    return salida
