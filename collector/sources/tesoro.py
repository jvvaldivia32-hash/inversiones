"""Tasa libre de riesgo de EE.UU. — bono del Tesoro a 1 año (curva "par yield", columna
"1 Yr"), del CSV público de home.treasury.gov. Gratis y sin API key: es lo que permite
tener el CAPM sin esperar la FRED_API_KEY (ver CLAUDE.md, Pendiente).

Se usa la tasa a 1 año del **inicio** de la ventana de un año del CAPM: es lo que un
inversionista habría asegurado sin riesgo ese día durante todo el período que se compara.
"""

import csv
import datetime
import io
import urllib.error
import urllib.request

URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{anio}/all?type=daily_treasury_yield_curve"
    "&field_tdr_date_value={anio}&page&_format=csv"
)
COLUMNA = "1 Yr"


class TesoroError(Exception):
    pass


def _descargar_anio(anio: int) -> list[tuple[datetime.date, float]]:
    req = urllib.request.Request(URL.format(anio=anio), headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            texto = resp.read().decode("utf-8-sig")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise TesoroError(f"treasury.gov no respondió: {e}") from e
    return _parsear(texto)


def _parsear(texto: str) -> list[tuple[datetime.date, float]]:
    filas = []
    for fila in csv.DictReader(io.StringIO(texto)):
        valor = (fila.get(COLUMNA) or "").strip()
        if not valor:
            continue
        mes, dia, anio = fila["Date"].split("/")
        filas.append((datetime.date(int(anio), int(mes), int(dia)), float(valor)))
    return filas


def tasa_1a(fecha: datetime.date) -> tuple[datetime.date, float]:
    """(fecha del dato, tasa en %) — el último dato publicado en o antes de `fecha`. Si
    `fecha` cae a comienzos de enero, el dato puede estar en el CSV del año anterior."""
    filas = [f for f in _descargar_anio(fecha.year) if f[0] <= fecha]
    if not filas:
        filas = [f for f in _descargar_anio(fecha.year - 1) if f[0] <= fecha]
    if not filas:
        raise TesoroError(f"sin tasa a 1 año publicada antes del {fecha}")
    return max(filas)
