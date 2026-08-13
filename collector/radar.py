import datetime

UMBRAL_MAXIMO_52S = 0.85  # "castigada" si el precio está bajo el 85% de su máximo — sección 3.3
DIAS_52_SEMANAS = 365
DIAS_MA200 = 200
MINIMO_PUNTOS_PARA_EVALUAR = 150  # sin esto, un ticker recién sembrado nunca calificaría


def _un_punto_por_dia(serie: list[dict]) -> list[dict]:
    por_dia = {p["ts"][:10]: p for p in serie}
    return [por_dia[dia] for dia in sorted(por_dia)]


def computar_castigada(serie: list[dict], ahora: datetime.datetime) -> dict | None:
    """{"precio", "maximo_52s", "pct_bajo_maximo", "ma_200", "bajo_ma200", "castigada"} o
    None si no hay suficiente historia todavía para evaluar en serio (recién sembrado, o
    Yahoo no devolvió backfill)."""
    diaria = _un_punto_por_dia(serie)
    if len(diaria) < MINIMO_PUNTOS_PARA_EVALUAR:
        return None

    ahora_sin_tz = ahora.replace(tzinfo=None) if ahora.tzinfo else ahora
    limite_52s = (ahora_sin_tz - datetime.timedelta(days=DIAS_52_SEMANAS)).isoformat()
    ultimo_52s = [p for p in diaria if p["ts"] >= limite_52s]
    if not ultimo_52s:
        return None

    precio = diaria[-1]["valor"]
    maximo_52s = max(p["valor"] for p in ultimo_52s)
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
