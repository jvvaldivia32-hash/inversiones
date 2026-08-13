import re
from html.parser import HTMLParser

from . import edgar, gemini

FORMULARIO_RESULTADOS = "8-K"
ITEM_RESULTADOS = "2.02"  # "Results of Operations and Financial Condition"


class _ExtractorTexto(HTMLParser):
    def __init__(self):
        super().__init__()
        self._en_ignorado = False
        self.partes: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._en_ignorado = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._en_ignorado = False

    def handle_data(self, data):
        if not self._en_ignorado:
            self.partes.append(data)


def _html_a_texto(html: str) -> str:
    extractor = _ExtractorTexto()
    extractor.feed(html)
    texto = "".join(extractor.partes)
    texto = re.sub(r"[ \t]+", " ", texto)
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def _es_exhibit_991(nombre_archivo: str) -> bool:
    # Nombres reales vistos: "msft-ex99_1.htm", "d159922dex991.htm",
    # "a8-kex991q3202606272026.htm", "exhibit991-6302026.htm" — sin convención única entre
    # filers, pero todos traen "ex" y "991" en algún orden una vez sacados los separadores.
    normalizado = re.sub(r"[^a-z0-9]", "", nombre_archivo.lower())
    return "ex" in normalizado and "991" in normalizado


def _buscar_exhibit_991(cik: str) -> tuple[str, str] | None:
    """(accession, url) del exhibit del 8-K de resultados (item 2.02) más reciente.

    None si no hay un 8-K de resultados, o si lo hay pero ninguno de sus documentos
    parece el press release (pasó con MCD antes de que se agregaran ambos exhibits al
    índice — no todos los filers lo llaman igual, ver `_es_exhibit_991`)."""
    data = edgar._request(f"{edgar.BASE_URL}/submissions/CIK{cik}.json")
    recientes = data.get("filings", {}).get("recent", {})
    formularios = recientes.get("form", [])
    items = recientes.get("items", [])
    accesiones = recientes.get("accessionNumber", [])

    for i, forma in enumerate(formularios):
        if forma != FORMULARIO_RESULTADOS or ITEM_RESULTADOS not in items[i]:
            continue

        accn = accesiones[i]
        accn_sin_guiones = accn.replace("-", "")
        cik_sin_ceros = str(int(cik))
        idx = edgar._request(
            f"https://www.sec.gov/Archives/edgar/data/{cik_sin_ceros}/{accn_sin_guiones}/index.json"
        )
        for item in idx.get("directory", {}).get("item", []):
            nombre = item.get("name", "")
            if _es_exhibit_991(nombre):
                url = (
                    f"https://www.sec.gov/Archives/edgar/data/{cik_sin_ceros}/"
                    f"{accn_sin_guiones}/{nombre}"
                )
                return accn, url
        return None  # el 8-K de resultados más reciente no trajo un exhibit reconocible

    return None


def obtener_segmentos(cik: str, accession_anterior: str | None) -> dict | None:
    """{"segmentos": [...], "_accession": "..."} si hay un press release nuevo con algo
    extraíble, o None si no cambió nada o no hay nada procesable. Quien llama decide si
    conserva el valor anterior — mismo criterio de degradación que sources/edgar.py."""
    encontrado = _buscar_exhibit_991(cik)
    if encontrado is None:
        return None
    accession, url = encontrado
    if accession == accession_anterior:
        return None

    html = edgar.request_texto(url)
    texto = _html_a_texto(html)
    lista = gemini.extraer_segmentos(texto)
    if lista is None:
        return None
    return {"segmentos": lista, "_accession": accession, "fuente_url": url}
