import json
import os
import urllib.error
import urllib.request

# Confirmado a mano contra la API real con la key real (2026-08-13): el endpoint clásico
# `models/{modelo}:generateContent` está deprecado para cuentas nuevas ("no longer available
# to new users" — 404), hay que usar la API de Interactions. `gemini-flash-lite-latest` da
# el mismo resultado de calidad que `gemini-flash-latest`/`gemini-3.6-flash` para tareas de
# clasificación/reescritura simples, pero con total_thought_tokens=0 (los otros gastan
# cientos de tokens de "pensamiento" que no necesitamos acá) — más barato, mismo tier gratis.
URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
MODELO = "gemini-flash-lite-latest"


def _llamar(prompt: str, schema: dict) -> dict | None:
    """Pide JSON estricto contra `schema`. None si falla cualquier cosa — sin key, red,
    respuesta no completada, JSON inválido — mismo criterio de degradación que
    banco_central.py/prices.py: quien llama decide qué hacer sin datos nuevos."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None

    body = {
        "model": MODELO,
        "input": prompt,
        "response_format": {"type": "text", "mime_type": "application/json", "schema": schema},
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        # TimeoutError no es subclase de URLError (viene de socket, no de urllib) — probado
        # de verdad: la llamada de reescribir_resumenes con varios grupos tardó más de 30s
        # y reventó sin este catch en vez de degradar como el resto del collector.
        return None

    if data.get("status") != "completed":
        return None

    for paso in data.get("steps", []):
        if paso.get("type") != "model_output":
            continue
        for parte in paso.get("content", []):
            if parte.get("type") == "text":
                try:
                    return json.loads(parte["text"])
                except (json.JSONDecodeError, KeyError, TypeError):
                    return None
    return None


def _es_copia_literal(texto: str, originales: list[str], n_palabras: int = 8) -> bool:
    """True si `texto` contiene una racha de `n_palabras` consecutivas que aparece tal cual
    (normalizada) en alguno de `originales` — señal de que Gemini copió en vez de reescribir.
    Regla dura de copyright (CLAUDE.md): nunca guardar un resumen/extracto que falle esto,
    sin importar lo que haya pedido el prompt."""
    palabras_texto = texto.lower().split()
    if len(palabras_texto) < n_palabras:
        return False
    rachas_texto = {
        " ".join(palabras_texto[i : i + n_palabras])
        for i in range(len(palabras_texto) - n_palabras + 1)
    }
    for original in originales:
        palabras_orig = original.lower().split()
        for i in range(len(palabras_orig) - n_palabras + 1):
            if " ".join(palabras_orig[i : i + n_palabras]) in rachas_texto:
                return True
    return False


def _cita_existe(cita: str, documento: str) -> bool:
    """True si `cita` aparece tal cual (solo tolerando diferencias de espacios/saltos de
    línea, nada más) como substring literal de `documento`. Regla dura del plan madre:
    toda cifra de segmento que Gemini extraiga de un press release debe venir con una cita
    que exista de verdad en el documento — si no, se descarta la extracción completa, no
    solo la cita."""
    normalizar = lambda t: " ".join(t.split())
    return normalizar(cita) in normalizar(documento)


def extraer_segmentos(texto_press_release: str) -> list[dict] | None:
    """Cifras de desempeño por segmento (ej. "Azure +43%") que el press release destaca
    explícitamente, cada una con su cita textual verificada contra el documento original.
    None si Gemini no está disponible o la llamada falla — quien llama decide qué hacer sin
    datos nuevos. Lista vacía (no None) si Gemini respondió pero no encontró nada, o si todo
    lo que encontró falló la validación de cita."""
    texto_press_release = texto_press_release.strip()
    if not texto_press_release:
        return []

    prompt = (
        "Este es el texto de un press release de resultados trimestrales. Identifica las "
        "cifras de desempeño por segmento o línea de negocio que la empresa destaca "
        'explícitamente (ej: "Azure revenue grew 43%", "comparable sales increased 2.5%"). '
        "Para cada una: el nombre del segmento, el porcentaje de variación, y la cita "
        "textual EXACTA — copiada palabra por palabra, sin cambiar ni una coma — de la "
        "oración del documento que contiene esa cifra. La cita se valida después contra el "
        "documento original y se descarta si no calza exacto, así que no la parafrasees. No "
        "inventes cifras que no estén en el texto. Si no hay ninguna, devuelve una lista "
        f"vacía.\n\n{texto_press_release}"
    )
    schema = {
        "type": "object",
        "properties": {
            "segmentos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "nombre": {"type": "string"},
                        "var_pct": {"type": "number"},
                        "cita": {"type": "string"},
                    },
                    "required": ["nombre", "var_pct", "cita"],
                },
            }
        },
        "required": ["segmentos"],
    }

    resultado = _llamar(prompt, schema)
    if resultado is None:
        return None
    segmentos = resultado.get("segmentos")
    if not isinstance(segmentos, list):
        return None

    salida = []
    for s in segmentos:
        if not isinstance(s, dict):
            continue
        nombre = s.get("nombre")
        var_pct = s.get("var_pct")
        cita = s.get("cita")
        if not (
            isinstance(nombre, str)
            and nombre.strip()
            and isinstance(var_pct, (int, float))
            and not isinstance(var_pct, bool)
            and isinstance(cita, str)
            and cita.strip()
        ):
            continue
        if not _cita_existe(cita, texto_press_release):
            continue
        salida.append({"nombre": nombre.strip(), "var_pct": var_pct, "cita": cita.strip()})
    return salida


def agrupar_historias(titulares: list[str]) -> list[tuple[str, list[int]]] | None:
    """Agrupa índices de `titulares` que se refieren al mismo hecho concreto, con un título
    neutral por grupo. None si Gemini no está disponible o la respuesta no sirve — quien
    llama debe caer al fallback por keywords. Cualquier titular no agrupado por Gemini (o si
    Gemini inventa un índice fuera de rango) queda como su propia historia de una sola
    fuente, nunca se descarta silenciosamente."""
    if not titulares:
        return []

    lineas = "\n".join(f"{i}: {t}" for i, t in enumerate(titulares))
    prompt = (
        "Agrupa estos titulares por historia. Dos titulares son la misma historia si se "
        "refieren al mismo hecho concreto. No agrupes por tema general, solo por hecho "
        "específico. No inventes historias que no estén en la lista.\n\n"
        f"{lineas}\n\n"
        "Para cada grupo da un título neutral en español, factual, sin adjetivos, y los "
        "índices de los titulares que pertenecen a ese grupo."
    )
    schema = {
        "type": "object",
        "properties": {
            "historias": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "titulo_neutral": {"type": "string"},
                        "indices": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["titulo_neutral", "indices"],
                },
            }
        },
        "required": ["historias"],
    }

    resultado = _llamar(prompt, schema)
    if resultado is None:
        return None
    historias = resultado.get("historias")
    if not isinstance(historias, list):
        return None

    n = len(titulares)
    vistos: set[int] = set()
    grupos: list[tuple[str, list[int]]] = []
    for h in historias:
        if not isinstance(h, dict):
            continue
        titulo = h.get("titulo_neutral")
        indices = h.get("indices")
        if not isinstance(titulo, str) or not titulo.strip() or not isinstance(indices, list):
            continue
        indices_validos = [
            i for i in indices if isinstance(i, int) and 0 <= i < n and i not in vistos
        ]
        if not indices_validos:
            continue
        vistos.update(indices_validos)
        grupos.append((titulo.strip(), indices_validos))

    for i in range(n):
        if i not in vistos:
            grupos.append((titulares[i], [i]))
    return grupos


def reescribir_resumenes(
    items: list[str], min_frases: int = 1, max_frases: int = 2
) -> list[str | None] | None:
    """`items[i]` es el snippet original (RSS) de una historia o artículo. Devuelve un
    resumen reescrito de `min_frases`-`max_frases` por índice, o None en esa posición si
    Gemini no pudo o si el resultado resultó ser una copia literal del original (regla dura
    de copyright — se aplica acá adentro, quien llama nunca recibe una copia). None (no la
    lista) si la llamada completa falló.

    El default 1-2 es el que exige la regla dura de copyright para `extracto` (por
    artículo, noticias por ticker) — quien llame para `resumen` de historia agrupada
    (Mundo/Chile) puede pedir más frases porque ahí no aplica ese tope."""
    if not items:
        return []
    lineas = "\n".join(f"{i}: {texto}" for i, texto in enumerate(items) if texto)
    if not lineas:
        return [None] * len(items)

    prompt = (
        f"Para cada fragmento de noticia numerado abajo, escribe un resumen neutral de "
        f"{min_frases} a {max_frases} frases en español, factual, SIN copiar frases "
        "textuales del original — reescribe con tus propias palabras el mismo hecho, con "
        "el contexto suficiente para entender qué pasó y por qué importa sin tener que leer "
        "la noticia original. Si un índice no tiene texto suficiente para resumir, omítelo "
        "de la respuesta.\n\n"
        f"{lineas}"
    )
    schema = {
        "type": "object",
        "properties": {
            "resumenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "indice": {"type": "integer"},
                        "resumen": {"type": "string"},
                    },
                    "required": ["indice", "resumen"],
                },
            }
        },
        "required": ["resumenes"],
    }

    resultado = _llamar(prompt, schema)
    if resultado is None:
        return None
    lista = resultado.get("resumenes")
    if not isinstance(lista, list):
        return None

    salida: list[str | None] = [None] * len(items)
    for r in lista:
        if not isinstance(r, dict):
            continue
        i = r.get("indice")
        resumen = r.get("resumen")
        if not (isinstance(i, int) and 0 <= i < len(items) and isinstance(resumen, str)):
            continue
        resumen = resumen.strip()
        if not resumen or _es_copia_literal(resumen, [items[i]]):
            continue
        salida[i] = resumen
    return salida
