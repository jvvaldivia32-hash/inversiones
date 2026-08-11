import re
from pathlib import Path

# Mismo patrón que TICKER_VALIDO en web/api/watchlist.ts — son las dos puntas de la misma
# tubería (un lado escribe watchlist.txt, este lado lo lee). Mantenerlos idénticos.
TICKER_VALIDO = re.compile(r"^[A-Z0-9.]{1,10}$")


def parse_watchlist(ruta: Path) -> list[str]:
    tickers = []
    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        ticker = linea.strip().upper()
        if not ticker:
            continue
        if not TICKER_VALIDO.match(ticker):
            print(f"watchlist: línea ignorada, no es un ticker válido: {linea!r}")
            continue
        tickers.append(ticker)
    return tickers
