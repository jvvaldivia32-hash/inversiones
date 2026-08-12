import datetime
import json
import os
from pathlib import Path

import historico
from env import cargar_env
from sources import prices, yahoo
from watchlist import parse_watchlist

RAIZ_REPO = Path(__file__).resolve().parent.parent
RUTA_HISTORICO = RAIZ_REPO / "data" / "historico_precios.json"
RUTA_DAILY = RAIZ_REPO / "data" / "daily.json"

CLAVES_ESPERADAS = [
    "GEMINI_API_KEY",
    "FINNHUB_KEY",
    "SEC_USER_AGENT",
    "BCCH_USER",
    "BCCH_PASS",
]


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


def construir_posiciones(
    tickers: list[str], hist: dict, cotizaciones: dict, ahora: datetime.datetime
) -> list[dict]:
    posiciones = []
    for ticker in tickers:
        if ticker not in cotizaciones:
            continue
        posiciones.append(
            {
                "ticker": ticker,
                "nombre": ticker,
                "precio": cotizaciones[ticker]["precio"],
                "var_dia_pct": cotizaciones[ticker]["var_dia_pct"],
                "serie_precio": historico.derivar_rangos(hist.get(ticker, []), ahora),
            }
        )
    return posiciones


def actualizar_daily_json(posiciones: list[dict], ahora: datetime.datetime) -> None:
    """Reemplaza `posiciones` en data/daily.json con datos reales, sin tocar el resto
    (bloques, referencias, radar, errores) — esas fases todavía no existen."""
    daily = json.loads(RUTA_DAILY.read_text(encoding="utf-8"))
    daily["posiciones"] = posiciones
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

    posiciones = construir_posiciones(tickers, hist, cotizaciones, ahora)
    actualizar_daily_json(posiciones, ahora)
    print(f"\ndata/daily.json actualizado con {len(posiciones)} posiciones reales.")

    print("\nRangos derivados:")
    for ticker in tickers:
        rangos = historico.derivar_rangos(hist.get(ticker, []), ahora)
        resumen = ", ".join(f"{r}={len(p)}pts" for r, p in rangos.items())
        print(f"  {ticker}: {resumen}")


if __name__ == "__main__":
    main()
