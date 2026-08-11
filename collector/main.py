from pathlib import Path

from watchlist import parse_watchlist

RAIZ_REPO = Path(__file__).resolve().parent.parent


def main() -> None:
    tickers = parse_watchlist(RAIZ_REPO / "watchlist.txt")
    print(f"Watchlist ({len(tickers)}): {', '.join(tickers)}")


if __name__ == "__main__":
    main()
