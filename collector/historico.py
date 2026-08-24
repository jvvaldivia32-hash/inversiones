import datetime
import json
from pathlib import Path

# Escalera de resolución (cambiada 2026-08-21, pedido de José de llegar a 10 años). La
# idea: guardar solo la resolución que el gráfico realmente dibuja en cada tramo. El rango
# "5A"/"10A" ya se dibujaba con un punto por semana (ver _un_punto_por_semana), así que
# guardar 250 puntos por año para dibujar 52 era peso puro. Con esta escalera el archivo
# queda en ~1.270 puntos por ticker — prácticamente lo mismo que ocupaba con 5 años a un
# punto diario — pero con el doble de historia.
#
# Nada de lo que consume estos datos pierde precisión: radar.computar_castigada solo mira
# 52 semanas y la media de 200 días, metricas_avanzadas.calcular_beta usa los retornos
# diarios del año corrido, y derivar_rangos ya colapsaba a semanal de 1 año para arriba.
DIAS_RECIENTES = 45  # ventana con resolución horaria completa
DIAS_DIARIOS = 730  # ~2 años: de acá para atrás se guarda un punto por semana
DIAS_MAX = 3650  # ~10 años, después se descarta


def _sin_tz(momento: datetime.datetime) -> datetime.datetime:
    return momento.replace(tzinfo=None) if momento.tzinfo else momento


def cargar(ruta: Path) -> dict:
    if not ruta.exists():
        return {}
    return json.loads(ruta.read_text(encoding="utf-8"))


def guardar(ruta: Path, historico: dict) -> None:
    ruta.write_text(
        json.dumps(historico, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sembrar(historico: dict, ticker: str, puntos_diarios: list[dict]) -> None:
    """Carga el backfill de Stooq (una lista de {fecha, valor}) como puntos iniciales."""
    historico[ticker] = [
        {"ts": f"{p['fecha']}T00:00:00", "valor": p["valor"]} for p in puntos_diarios
    ]


def agregar_punto(historico: dict, ticker: str, ahora: datetime.datetime, valor: float) -> None:
    """Agrega el punto de esta hora. Deduplicado por balde de hora: si ya hay un punto de
    este ticker en la misma hora, no agrega otro (corridas repetidas / reintentos)."""
    ahora = _sin_tz(ahora)
    balde = ahora.replace(minute=0, second=0, microsecond=0).isoformat()
    serie = historico.setdefault(ticker, [])
    if serie and serie[-1]["ts"][:13] == balde[:13]:
        return
    serie.append({"ts": balde, "valor": valor})


def compactar(
    historico: dict,
    ahora: datetime.datetime,
    dias_recientes: int = DIAS_RECIENTES,
    dias_diarios: int = DIAS_DIARIOS,
    dias_max: int = DIAS_MAX,
) -> None:
    """Mantenimiento en tres tramos: los últimos `dias_recientes` quedan con resolución
    horaria completa; entre ahí y `dias_diarios` se colapsa a un punto por día; entre ahí y
    `dias_max` a un punto por semana; más viejo que `dias_max` se descarta."""
    ahora = _sin_tz(ahora)
    corte_reciente = ahora - datetime.timedelta(days=dias_recientes)
    corte_diario = ahora - datetime.timedelta(days=dias_diarios)
    corte_max = ahora - datetime.timedelta(days=dias_max)

    for ticker, serie in historico.items():
        recientes = []
        ultimo_del_dia: dict[str, dict] = {}
        ultimo_de_la_semana: dict[tuple, dict] = {}
        for punto in serie:
            ts = datetime.datetime.fromisoformat(punto["ts"])
            if ts < corte_max:
                continue
            if ts >= corte_reciente:
                recientes.append(punto)
            elif ts >= corte_diario:
                ultimo_del_dia[ts.date().isoformat()] = punto
            else:
                # isocalendar()[:2] = (año ISO, semana ISO) — misma clave de semana que usa
                # _un_punto_por_semana, así que lo que se guarda calza exactamente con lo
                # que el gráfico va a dibujar en "5A"/"10A".
                ultimo_de_la_semana[ts.date().isocalendar()[:2]] = punto

        semanales = sorted(ultimo_de_la_semana.values(), key=lambda p: p["ts"])
        diarios = sorted(ultimo_del_dia.values(), key=lambda p: p["ts"])
        recientes.sort(key=lambda p: p["ts"])
        historico[ticker] = semanales + diarios + recientes


def _un_punto_por_dia(puntos: list[dict]) -> list[dict]:
    por_dia = {p["ts"][:10]: p for p in puntos}  # último visto por día gana (orden asc.)
    return [{"fecha": dia, "valor": p["valor"]} for dia, p in sorted(por_dia.items())]


def _un_punto_por_semana(puntos: list[dict]) -> list[dict]:
    por_semana = {}
    for p in puntos:
        semana = datetime.date.fromisoformat(p["ts"][:10]).isocalendar()[:2]
        por_semana[semana] = p
    ordenados = sorted(por_semana.items(), key=lambda kv: kv[0])
    return [{"fecha": p["ts"][:10], "valor": p["valor"]} for _, p in ordenados]


def derivar_rangos(serie_completa: list[dict], ahora: datetime.datetime) -> dict:
    """Arma las 6 claves que espera SeriePrecio en web/src/types.ts, sin cambiar ese
    contrato: {fecha, valor}[] para cada rango. 1M usa timestamp completo como `fecha`
    (formatFechaCorta del frontend igual solo muestra día/mes) para que cada punto horario
    quede como una categoría distinta en el eje X — si se truncara a fecha, los puntos de
    un mismo día se apilarían en el mismo lugar del gráfico."""
    ahora = _sin_tz(ahora)

    def filtrar(dias):
        limite = ahora - datetime.timedelta(days=dias)
        return [p for p in serie_completa if datetime.datetime.fromisoformat(p["ts"]) >= limite]

    un_mes = [{"fecha": p["ts"], "valor": p["valor"]} for p in filtrar(30)]

    return {
        "1M": un_mes,
        "6M": _un_punto_por_dia(filtrar(180)),
        "YTD": _un_punto_por_dia(
            [p for p in serie_completa if p["ts"][:10] >= f"{ahora.year}-01-01"]
        ),
        "1A": _un_punto_por_dia(filtrar(365)),
        "5A": _un_punto_por_semana(filtrar(1825)),
        "10A": _un_punto_por_semana(filtrar(DIAS_MAX)),
    }
