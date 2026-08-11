import os
from pathlib import Path

from env import cargar_env
from watchlist import parse_watchlist

RAIZ_REPO = Path(__file__).resolve().parent.parent

CLAVES_ESPERADAS = [
    "GEMINI_API_KEY",
    "FINNHUB_KEY",
    "SEC_USER_AGENT",
    "BCCH_USER",
    "BCCH_PASS",
]


def main() -> None:
    cargar_env(RAIZ_REPO / ".env")

    tickers = parse_watchlist(RAIZ_REPO / "watchlist.txt")
    print(f"Watchlist ({len(tickers)}): {', '.join(tickers)}")

    print("Variables de entorno:")
    for clave in CLAVES_ESPERADAS:
        estado = "detectada" if os.environ.get(clave) else "no seteada"
        print(f"  {clave}: {estado}")


if __name__ == "__main__":
    main()
