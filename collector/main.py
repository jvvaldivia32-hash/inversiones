import datetime
import json
import os
from pathlib import Path

import historico
import noticias
import tesis
from env import cargar_env
from sources import banco_central, edgar, prices, segmentos, yahoo
from watchlist import parse_watchlist

RAIZ_REPO = Path(__file__).resolve().parent.parent
RUTA_HISTORICO = RAIZ_REPO / "data" / "historico_precios.json"
RUTA_DAILY = RAIZ_REPO / "data" / "daily.json"
RUTA_TESIS = RAIZ_REPO / "data" / "tesis.json"

CLAVES_ESPERADAS = [
    "GEMINI_API_KEY",
    "FINNHUB_KEY",
    "SEC_USER_AGENT",
    "BCCH_API_KEY",
]

INDICES_REFERENCIA = {
    "VOO": "Vanguard S&P 500 ETF",
    "QQQ": "Invesco QQQ (Nasdaq-100)",
    "VTI": "Vanguard Total Stock Market ETF",
}


def actualizar_precios(tickers: list[str], ahora: datetime.datetime) -> tuple[dict, dict]:
    hist = historico.cargar(RUTA_HISTORICO)
    cotizaciones = {}

    for ticker in tickers:
        if ticker not in hist:
            print(f"{ticker}: sin historia, sembrando desde Yahoo Finance...")
            backfill = yahoo.descargar_historico(ticker)
            if backfill:
                historico.sembrar(hist, ticker, backfill)
                print(f"  {len(backfill)} días sembrados")
            else:
                print("  Yahoo no devolvió datos — arranca solo con lo que junte Finnhub")

        try:
            cotizacion = prices.obtener_cotizacion(ticker)
            historico.agregar_punto(hist, ticker, ahora, cotizacion["precio"])
            cotizaciones[ticker] = cotizacion
            print(f"{ticker}: {cotizacion['precio']}")
        except prices.FinnhubError as e:
            # Sin cotización nueva, el ticker no entra a `posiciones` esta corrida — mejor
            # que la card vuelva a "pendiente" un rato a que muestre un precio mentiroso.
            print(f"{ticker}: no se pudo actualizar el precio ({e})")

    historico.compactar(hist, ahora)
    historico.guardar(RUTA_HISTORICO, hist)
    return hist, cotizaciones


def _fundamentales_anteriores() -> dict[str, dict]:
    daily = json.loads(RUTA_DAILY.read_text(encoding="utf-8"))
    return {
        p["ticker"]: p["fundamentales"] for p in daily.get("posiciones", []) if p.get("fundamentales")
    }


def _obtener_fundamentales(ticker: str, anterior: dict | None) -> dict | None:
    """Fundamentales reales si hay un filing nuevo, o lo que había antes si EDGAR falla
    o no cambió nada — mismo criterio de degradación que sources/banco_central.py."""
    cik = edgar.CIK_POR_TICKER.get(ticker)
    if cik is None:
        return None
    accession_anterior = anterior.get("_accession") if anterior else None
    try:
        nuevo = edgar.obtener_fundamentales(ticker, cik, accession_anterior)
    except edgar.EdgarError as e:
        print(f"  {ticker}: fundamentales no se pudieron actualizar ({e})")
        return anterior
    return nuevo if nuevo is not None else anterior


def _segmentos_anteriores() -> dict[str, dict]:
    daily = json.loads(RUTA_DAILY.read_text(encoding="utf-8"))
    return {
        p["ticker"]: {
            "segmentos": p["segmentos"],
            "_accession": p.get("_segmentos_accession"),
            "fuente_url": p.get("segmentos_fuente_url"),
        }
        for p in daily.get("posiciones", [])
        if p.get("segmentos") is not None
    }


def _obtener_segmentos(ticker: str, anterior: dict | None) -> dict | None:
    """Igual que _obtener_fundamentales, pero para el press release del 8-K (Fase 5)."""
    cik = edgar.CIK_POR_TICKER.get(ticker)
    if cik is None:
        return None
    accession_anterior = anterior.get("_accession") if anterior else None
    try:
        nuevo = segmentos.obtener_segmentos(cik, accession_anterior)
    except edgar.EdgarError as e:
        print(f"  {ticker}: segmentos no se pudieron actualizar ({e})")
        return anterior
    return nuevo if nuevo is not None else anterior


def _cargar_tesis() -> list[dict]:
    if not RUTA_TESIS.exists():
        return []
    return json.loads(RUTA_TESIS.read_text(encoding="utf-8"))


def _guardar_tesis(lista: list[dict]) -> None:
    RUTA_TESIS.write_text(json.dumps(lista, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _es_dato_fresco(nuevo: dict | None, anterior: dict | None) -> bool:
    """True si `nuevo` trae un `_accession` distinto al de `anterior` (o no había
    anterior) — o sea, esta corrida trajo un filing de verdad nuevo, no un valor
    degradado/conservado de la corrida pasada. Fase 7 solo revisa tesis contra datos
    frescos: sin esto, cada corrida horaria repetiría la misma lectura una y otra vez."""
    if nuevo is None:
        return False
    return anterior is None or nuevo.get("_accession") != anterior.get("_accession")


def _revisar_tesis_ticker(
    tesis_lista: list[dict],
    ticker: str,
    ahora: datetime.datetime,
    fundamentales: dict | None,
    fundamentales_frescos: bool,
    segmentos_resultado: dict | None,
    segmentos_frescos: bool,
) -> None:
    """Muta `tesis_lista` in place: agrega una lectura a cada tesis activa de `ticker`
    si hay dato fresco de verdad esta corrida. Una lectura con semáforo rojo cierra la
    tesis como "rota" — el punto entero del rastreador es no dejar que se reescriba
    después de conocer el resultado."""
    if not fundamentales_frescos and not segmentos_frescos:
        return
    for t in tesis_lista:
        if t["ticker"] != ticker or t["estado"] != "activa":
            continue
        lectura = tesis.revisar_tesis(t, ahora, fundamentales, segmentos_resultado)
        if lectura is None:
            continue
        t["lecturas"].append(lectura)
        if lectura["semaforo"] == "rojo":
            t["estado"] = "rota"


def construir_posiciones(
    tickers: list[str], hist: dict, cotizaciones: dict, ahora: datetime.datetime
) -> list[dict]:
    fundamentales_anteriores = _fundamentales_anteriores()
    segmentos_anteriores = _segmentos_anteriores()
    tesis_lista = _cargar_tesis()
    posiciones = []
    for ticker in tickers:
        if ticker not in cotizaciones:
            continue
        posicion = {
            "ticker": ticker,
            "nombre": ticker,
            "precio": cotizaciones[ticker]["precio"],
            "var_dia_pct": cotizaciones[ticker]["var_dia_pct"],
            "serie_precio": historico.derivar_rangos(hist.get(ticker, []), ahora),
            "noticias": noticias.noticias_ticker(ticker),
        }

        anterior_fund = fundamentales_anteriores.get(ticker)
        fundamentales = _obtener_fundamentales(ticker, anterior_fund)
        fundamentales_frescos = _es_dato_fresco(fundamentales, anterior_fund)
        if fundamentales is not None:
            posicion["fundamentales"] = fundamentales

        anterior_seg = segmentos_anteriores.get(ticker)
        seg = _obtener_segmentos(ticker, anterior_seg)
        segmentos_frescos = _es_dato_fresco(seg, anterior_seg)
        if seg is not None:
            posicion["segmentos"] = seg["segmentos"]
            posicion["_segmentos_accession"] = seg["_accession"]
            posicion["segmentos_fuente_url"] = seg["fuente_url"]

        _revisar_tesis_ticker(
            tesis_lista, ticker, ahora, fundamentales, fundamentales_frescos, seg, segmentos_frescos
        )
        tesis_ticker = [t for t in tesis_lista if t["ticker"] == ticker]
        if tesis_ticker:
            posicion["tesis"] = tesis_ticker

        posiciones.append(posicion)

    _guardar_tesis(tesis_lista)
    return posiciones


def actualizar_referencias() -> dict:
    """Referencias con datos reales de Banco Central (Chile) y Finnhub (índices). Si una
    fuente puntual falla, se conserva el valor que ya estaba en daily.json para ese campo
    en particular — mejor un dato de hace un rato que uno en blanco."""
    daily = json.loads(RUTA_DAILY.read_text(encoding="utf-8"))
    referencias_anteriores = daily.get("referencias", {"indices": [], "chile": {}})

    chile_anterior = referencias_anteriores.get("chile", {})
    chile = {**chile_anterior, **banco_central.obtener_referencias_chile()}

    indices_anteriores = {i["ticker"]: i for i in referencias_anteriores.get("indices", [])}
    indices = []
    for ticker, nombre in INDICES_REFERENCIA.items():
        try:
            cot = prices.obtener_cotizacion(ticker)
            indices.append(
                {
                    "ticker": ticker,
                    "nombre": nombre,
                    "precio": cot["precio"],
                    "var_dia_pct": cot["var_dia_pct"],
                }
            )
        except prices.FinnhubError:
            anterior = indices_anteriores.get(ticker)
            if anterior:
                indices.append(anterior)

    return {"indices": indices, "chile": chile}


def actualizar_daily_json(
    posiciones: list[dict],
    bloques_noticias: tuple[list[dict], list[dict], list[dict]],
    errores_noticias: list[str],
    referencias: dict,
    ahora: datetime.datetime,
) -> None:
    """Reemplaza `posiciones`, `bloques` y `referencias` en data/daily.json con datos
    reales, sin tocar `radar` — esa fase todavía no existe."""
    mundo, chile, actualidad = bloques_noticias
    daily = json.loads(RUTA_DAILY.read_text(encoding="utf-8"))
    daily["posiciones"] = posiciones
    daily["bloques"] = {"mundo": mundo, "chile": chile, "actualidad": actualidad}
    daily["referencias"] = referencias
    daily["errores"] = errores_noticias
    daily["generado"] = ahora.isoformat()
    RUTA_DAILY.write_text(
        json.dumps(daily, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> None:
    cargar_env(RAIZ_REPO / ".env")

    tickers = parse_watchlist(RAIZ_REPO / "watchlist.txt")
    print(f"Watchlist ({len(tickers)}): {', '.join(tickers)}")

    print("Variables de entorno:")
    for clave in CLAVES_ESPERADAS:
        estado = "detectada" if os.environ.get(clave) else "no seteada"
        print(f"  {clave}: {estado}")

    if not os.environ.get("FINNHUB_KEY"):
        print("\nFINNHUB_KEY no está seteada, no se actualizan precios.")
        return

    print("\nActualizando precios...")
    ahora = datetime.datetime.now(datetime.timezone.utc)
    hist, cotizaciones = actualizar_precios(tickers, ahora)

    print("\nLeyendo noticias...")
    mundo, chile, actualidad, errores_noticias = noticias.recolectar_bloques()
    print(f"  mundo={len(mundo)} chile={len(chile)} actualidad={len(actualidad)}")
    for e in errores_noticias:
        print(f"  aviso: {e}")

    print("\nActualizando referencias (Banco Central + índices)...")
    referencias = actualizar_referencias()
    print(f"  chile: {referencias['chile']}")
    print(f"  indices: {[i['ticker'] for i in referencias['indices']]}")

    posiciones = construir_posiciones(tickers, hist, cotizaciones, ahora)
    actualizar_daily_json(
        posiciones, (mundo, chile, actualidad), errores_noticias, referencias, ahora
    )
    print(f"\ndata/daily.json actualizado con {len(posiciones)} posiciones reales.")

    print("\nRangos derivados:")
    for ticker in tickers:
        rangos = historico.derivar_rangos(hist.get(ticker, []), ahora)
        resumen = ", ".join(f"{r}={len(p)}pts" for r, p in rangos.items())
        print(f"  {ticker}: {resumen}")


if __name__ == "__main__":
    main()
