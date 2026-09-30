"""Riesgo y retorno por ticker, calculado del historial de precios ya guardado.

Sin APIs nuevas: todo sale de `historico_precios.json`. Tres medidas, elegidas por ser las
que un usuario cualquiera entiende sin haber estudiado finanzas:

- **Retorno anual** (geométrico / CAGR) a 1, 3, 5 y 10 años: "creció X% al año". Geométrico y
  no aritmético a propósito — el aritmético sobreestima lo que de verdad creció la plata
  cuando hay volatilidad (el geométrico siempre es ≤ el aritmético).
- **Volatilidad anual**: desviación estándar de los retornos diarios del último año,
  anualizada con √252 (días hábiles).
- **Caída máxima** en 5 años: la peor baja desde un máximo previo hasta un mínimo posterior.

Todo es sobre el **precio**, sin dividendos: para algo como VOO o MCD el retorno total real es
algo mayor. La vista lo dice explícitamente.
"""

import datetime
import math

DIAS_HABILES_POR_ANIO = 252
HORIZONTES_ANIOS = (1, 3, 5, 10)
# El punto más viejo guardado puede quedar unos días después del aniversario exacto (el
# historial se recorta a 3650 días y los findes no tienen dato): se acepta ese margen.
TOLERANCIA_DIAS = 15
MINIMO_RETORNOS_VOLATILIDAD = 150  # ~7 meses hábiles; con menos, el número no es serio
ANIOS_CAIDA_MAXIMA = 5


def _cierres_por_dia(historial: list[dict]) -> list[tuple[datetime.date, float]]:
    """Un precio por día hábil (el último del día), de lo más viejo a lo más nuevo.

    Se sacan sábados y domingos: el recolector corre también el fin de semana y guarda el
    cierre del viernes repetido. Esos "días" con variación 0% bajarían la volatilidad ~17%.
    """
    por_dia: dict[datetime.date, float] = {}
    for p in historial:
        dia = datetime.date.fromisoformat(p["ts"][:10])
        if dia.weekday() < 5 and p.get("valor"):
            por_dia[dia] = float(p["valor"])
    return sorted(por_dia.items())


def _retorno_anual(
    cierres: list[tuple[datetime.date, float]], hoy: datetime.date, anios: int
) -> float | None:
    objetivo = hoy - datetime.timedelta(days=round(365.25 * anios))
    inicio = next(((d, v) for d, v in cierres if d >= objetivo), None)
    if inicio is None or (inicio[0] - objetivo).days > TOLERANCIA_DIAS:
        return None  # no hay historia suficiente para ese horizonte: no se inventa
    fecha_ini, precio_ini = inicio
    fecha_fin, precio_fin = cierres[-1]
    anios_reales = (fecha_fin - fecha_ini).days / 365.25
    if anios_reales <= 0 or precio_ini <= 0:
        return None
    return ((precio_fin / precio_ini) ** (1 / anios_reales) - 1) * 100


def _volatilidad_anual(cierres: list[tuple[datetime.date, float]], hoy: datetime.date) -> float | None:
    desde = hoy - datetime.timedelta(days=365)
    valores = [v for d, v in cierres if d >= desde]
    retornos = [math.log(b / a) for a, b in zip(valores, valores[1:]) if a > 0 and b > 0]
    if len(retornos) < MINIMO_RETORNOS_VOLATILIDAD:
        return None
    media = sum(retornos) / len(retornos)
    varianza = sum((r - media) ** 2 for r in retornos) / (len(retornos) - 1)
    return math.sqrt(varianza) * math.sqrt(DIAS_HABILES_POR_ANIO) * 100


def _caida_maxima(cierres: list[tuple[datetime.date, float]], hoy: datetime.date) -> float | None:
    desde = hoy - datetime.timedelta(days=round(365.25 * ANIOS_CAIDA_MAXIMA))
    valores = [v for d, v in cierres if d >= desde]
    if len(valores) < 2:
        return None
    maximo, peor = valores[0], 0.0
    for v in valores:
        maximo = max(maximo, v)
        peor = min(peor, v / maximo - 1)
    return peor * 100


def calcular(historial: list[dict], ahora: datetime.datetime) -> dict | None:
    """{"retorno_anual_pct": {"1A": .., "5A": ..}, "volatilidad_anual_pct", "caida_maxima_5a_pct"}
    con solo lo que se pudo calcular. None si no hay nada (ticker recién agregado)."""
    cierres = _cierres_por_dia(historial)
    if len(cierres) < 2:
        return None
    hoy = ahora.date()

    retornos = {}
    for anios in HORIZONTES_ANIOS:
        r = _retorno_anual(cierres, hoy, anios)
        if r is not None:
            retornos[f"{anios}A"] = r

    salida: dict = {}
    if retornos:
        salida["retorno_anual_pct"] = retornos
    vol = _volatilidad_anual(cierres, hoy)
    if vol is not None:
        salida["volatilidad_anual_pct"] = vol
    caida = _caida_maxima(cierres, hoy)
    if caida is not None:
        salida["caida_maxima_5a_pct"] = caida
    return salida or None
