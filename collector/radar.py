import datetime

UMBRAL_MAXIMO_52S = 0.85  # "castigada" si el precio está bajo el 85% de su máximo — sección 3.3
DIAS_52_SEMANAS = 365
DIAS_MA200 = 200
MINIMO_PUNTOS_PARA_EVALUAR = 150  # sin esto, un ticker recién sembrado nunca calificaría

DEUDA_PATRIMONIO_MAXIMA = 2  # sección 3.3 — no aplica a bancos

# Bancos donde deuda/patrimonio no es una señal de salud (los depósitos son pasivo, es el
# modelo de negocio) — sección 3.3 del plan lo dice para JPM/BAC/GS explícitamente; se
# extiende acá a BCH/BSAC porque son bancos por el mismo motivo, aunque el plan los liste
# bajo "ADRs chilenos" y no bajo "Bancos" — juicio propio, señalado por si no calza con lo
# que el usuario tenía en mente.
BANCOS = {"JPM", "BAC", "GS", "BCH", "BSAC"}


def _un_punto_por_dia(serie: list[dict]) -> list[dict]:
    por_dia = {p["ts"][:10]: p for p in serie}
    return [por_dia[dia] for dia in sorted(por_dia)]


def maximo_minimo_52s(serie: list[dict], ahora: datetime.datetime) -> tuple[float, float] | None:
    """(máximo, mínimo) de los últimos 365 días de `serie`, o None si no hay ningún punto
    dentro de esa ventana — extraído de computar_castigada() para reusar en métricas
    avanzadas (52wk High/Low por posición) sin duplicar la ventana de fechas."""
    diaria = _un_punto_por_dia(serie)
    ahora_sin_tz = ahora.replace(tzinfo=None) if ahora.tzinfo else ahora
    limite_52s = (ahora_sin_tz - datetime.timedelta(days=DIAS_52_SEMANAS)).isoformat()
    ultimo_52s = [p for p in diaria if p["ts"] >= limite_52s]
    if not ultimo_52s:
        return None
    valores = [p["valor"] for p in ultimo_52s]
    return max(valores), min(valores)


def computar_castigada(serie: list[dict], ahora: datetime.datetime) -> dict | None:
    """{"precio", "maximo_52s", "pct_bajo_maximo", "ma_200", "bajo_ma200", "castigada"} o
    None si no hay suficiente historia todavía para evaluar en serio (recién sembrado, o
    Yahoo no devolvió backfill)."""
    diaria = _un_punto_por_dia(serie)
    if len(diaria) < MINIMO_PUNTOS_PARA_EVALUAR:
        return None

    extremos = maximo_minimo_52s(serie, ahora)
    if extremos is None:
        return None
    maximo_52s, _minimo_52s = extremos

    precio = diaria[-1]["valor"]
    pct_bajo_maximo = (maximo_52s - precio) / maximo_52s * 100

    ultimos_200 = diaria[-DIAS_MA200:]
    ma_200 = sum(p["valor"] for p in ultimos_200) / len(ultimos_200)
    bajo_ma200 = precio < ma_200

    castigada = pct_bajo_maximo >= (1 - UMBRAL_MAXIMO_52S) * 100 or bajo_ma200

    return {
        "precio": precio,
        "maximo_52s": maximo_52s,
        "pct_bajo_maximo": round(pct_bajo_maximo, 1),
        "ma_200": round(ma_200, 2),
        "bajo_ma200": bajo_ma200,
        "castigada": castigada,
    }


def evaluar_sana(series: dict, deuda_patrimonio: float | None, es_banco: bool) -> dict | None:
    """{"sana": bool, "motivos": [...]} evaluando los 5 criterios obligatorios de la
    sección 3.3 contra `series` (el shape de Fundamentales.series ya calculado por
    edgar.obtener_fundamentales). None si no hay suficiente dato real para evaluar en
    serio — mejor no aparecer en el radar que aparecer con un motivo inventado."""
    ingresos = series.get("ingresos_musd") or []
    margen = series.get("margen_operativo") or []
    flujo_op = series.get("flujo_op_musd") or []

    if len(ingresos) < 5 or not margen or not flujo_op:
        return None
    if not es_banco and deuda_patrimonio is None:
        return None

    motivos = []

    if ingresos[-1]["valor"] <= ingresos[-5]["valor"]:
        motivos.append("ingresos cayendo interanual")

    if margen[-1]["valor"] <= 0:
        motivos.append("margen operativo negativo")

    ultimos_5 = ingresos[-5:]
    trimestres_positivos = sum(
        1 for i in range(1, 5) if ultimos_5[i]["valor"] > ultimos_5[i - 1]["valor"]
    )
    if trimestres_positivos < 3:
        motivos.append(f"ingresos creciendo solo {trimestres_positivos} de los últimos 4 trimestres")

    if flujo_op[-1]["valor"] <= 0:
        motivos.append("flujo operativo negativo")

    if not es_banco and deuda_patrimonio >= DEUDA_PATRIMONIO_MAXIMA:
        motivos.append(f"deuda/patrimonio {deuda_patrimonio:.1f} (alto)")

    return {"sana": len(motivos) == 0, "motivos": motivos}
