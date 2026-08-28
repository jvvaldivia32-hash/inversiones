"""Avisos por Telegram cuando un ticker vigilado se mueve fuerte en el día.

Corre pegado al recolector horario (collector/main.py), así que el aviso sale en el mismo
run que detecta el movimiento — no hay un segundo cron esperando.

Qué NO hace, a propósito: no dice qué hacer con el movimiento. Igual que el Radar, esto
muestra el dato y la noticia que hay detrás; la decisión es del usuario (regla dura de
CLAUDE.md).
"""

import datetime
import json
from pathlib import Path

from formato import num, pct
from sources import prices, telegram

RAIZ_REPO = Path(__file__).resolve().parent.parent
RUTA_ESTADO = RAIZ_REPO / "data" / "alertas_enviadas.json"

# Movimiento diario, en valor absoluto, que gatilla el aviso. ±5% es raro pero no
# excéntrico: suena por resultados, guidance o un batacazo del mercado, no por un día
# nervioso cualquiera. Decidido con el usuario el 2026-08-27.
UMBRAL_PCT = 5.0


def _hoy(ahora: datetime.datetime) -> str:
    """Día de mercado según Nueva York, no según UTC.

    Con UTC, una sesión que cierra a las 20:00 UTC y otra que abre al día siguiente caen en
    fechas distintas — pero un run de las 00:30 UTC todavía habla de la sesión de *ayer* en
    Nueva York, y con UTC se le reiniciaría el antiduplicado y volvería a avisar lo mismo.
    """
    return (ahora.astimezone(datetime.timezone.utc) - datetime.timedelta(hours=5)).strftime(
        "%Y-%m-%d"
    )


def cargar_estado(ruta: Path = RUTA_ESTADO) -> dict:
    try:
        estado = json.loads(ruta.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"fecha": None, "avisados": {}}
    return {"fecha": estado.get("fecha"), "avisados": estado.get("avisados", {})}


def guardar_estado(estado: dict, ruta: Path = RUTA_ESTADO) -> None:
    ruta.write_text(json.dumps(estado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def detectar(movimientos: list[dict], estado: dict, hoy: str, umbral: float = UMBRAL_PCT) -> tuple[list[dict], dict]:
    """Filtra los movimientos que ameritan aviso y devuelve el estado antiduplicado nuevo.

    Un ticker no vuelve a avisar el mismo día *salvo* que se haya movido otro `umbral`
    completo desde el último aviso: si TSLA cae 5% avisa, si sigue hasta 10% vuelve a
    avisar, pero los pasos intermedios (5,4% → 6,1% → 7,8%) no llenan el celular.
    """
    avisados = dict(estado["avisados"]) if estado.get("fecha") == hoy else {}

    alertas = []
    for mov in movimientos:
        var = mov.get("var_dia_pct")
        if var is None or abs(var) < umbral:
            continue

        anterior = avisados.get(mov["ticker"])
        if anterior is not None and abs(var) < abs(anterior) + umbral:
            continue

        alertas.append(mov)
        avisados[mov["ticker"]] = var

    return alertas, {"fecha": hoy, "avisados": avisados}


def formatear(alertas: list[dict]) -> str:
    """Un bloque por ticker: qué se movió, cuánto, a qué precio y la noticia si la hay."""
    partes = []
    for a in alertas:
        flecha = "🔺" if a["var_dia_pct"] > 0 else "🔻"
        linea = f"{flecha} <b>{telegram.escapar(a['ticker'])}</b> {pct(a['var_dia_pct'])} hoy\n"

        # `nombre` viene igual al ticker para la watchlist (main.py todavía no resuelve el
        # nombre largo), y repetirlo se lee raro: "BRK.B · BRK.B · US$ 504,91".
        detalle = [] if (a.get("nombre") or a["ticker"]) == a["ticker"] else [telegram.escapar(a["nombre"])]
        detalle.append(f"US$ {num(a['precio'])}")
        if a.get("origen"):
            detalle.append(a["origen"])
        linea += " · ".join(detalle)

        noticia = a.get("noticia")
        if noticia:
            linea += (
                f"\n\n<i>{telegram.escapar(noticia['titular'])}</i>\n"
                f'<a href="{telegram.escapar(noticia["url"])}">{telegram.escapar(noticia["medio"])}</a>'
            )
        partes.append(linea)

    encabezado = "Movimiento fuerte" if len(partes) == 1 else f"{len(partes)} movimientos fuertes"
    return f"<b>{encabezado}</b> (±{num(UMBRAL_PCT, 0)}% en el día)\n\n" + "\n\n———\n\n".join(partes)


def recolectar_movimientos(daily: dict) -> list[dict]:
    """Variación del día de todo lo vigilado: watchlist + candidatos del Radar.

    La watchlist sale gratis de `daily.json` (el recolector le acaba de pedir el precio a
    Finnhub). Los candidatos del Radar no: su `serie_precio` solo se refresca en el cron
    semanal, así que su variación diaria hay que pedirla — son ~16 quotes por hora, muy
    dentro del free tier de Finnhub (60 llamadas por minuto), y no se guardan en el
    histórico para no engordarlo con tickers que el Radar puede sacar la semana que viene.
    """
    movimientos = []
    vistos = set()

    for pos in daily.get("posiciones", []):
        noticias = pos.get("noticias") or []
        movimientos.append(
            {
                "ticker": pos["ticker"],
                "nombre": pos.get("nombre"),
                "precio": pos.get("precio"),
                "var_dia_pct": pos.get("var_dia_pct"),
                "origen": "watchlist",
                "noticia": noticias[0] if noticias else None,
            }
        )
        vistos.add(pos["ticker"])

    for cand in daily.get("radar", {}).get("candidatos", []):
        if cand["ticker"] in vistos:  # ya vino por watchlist, con precio fresco y noticia
            continue
        try:
            cot = prices.obtener_cotizacion(cand["ticker"])
        except prices.FinnhubError as e:
            print(f"  {cand['ticker']}: sin cotización para alertas ({e})")
            continue
        movimientos.append(
            {
                "ticker": cand["ticker"],
                "nombre": cand.get("nombre"),
                "precio": cot["precio"],
                "var_dia_pct": cot["var_dia_pct"],
                "origen": "Radar",
                "noticia": None,
            }
        )
        vistos.add(cand["ticker"])

    return movimientos


def revisar(daily: dict, ahora: datetime.datetime, ruta_estado: Path = RUTA_ESTADO) -> list[dict]:
    """Punto de entrada desde main.py. Devuelve las alertas efectivamente enviadas."""
    if not telegram.configurado():
        print("  Telegram sin configurar, no se revisan alertas")
        return []

    hoy = _hoy(ahora)
    movimientos = recolectar_movimientos(daily)
    alertas, estado = detectar(movimientos, cargar_estado(ruta_estado), hoy)

    if not alertas:
        print(f"  sin movimientos de ±{UMBRAL_PCT}% entre {len(movimientos)} tickers vigilados")
        return []

    if not telegram.enviar(formatear(alertas)):
        # No se guarda el estado si el envío falló: así el próximo run reintenta en vez de
        # dar por avisado algo que nunca llegó al celular.
        return []

    guardar_estado(estado, ruta_estado)
    print(f"  avisados por Telegram: {', '.join(a['ticker'] for a in alertas)}")
    return alertas
