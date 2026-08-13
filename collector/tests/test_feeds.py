import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import feeds


def test_feed_noticias_ticker_usa_guion_para_clases_de_accion():
    assert "s=BRK-B" in feeds.feed_noticias_ticker("BRK.B")


def test_feed_noticias_ticker_no_toca_tickers_sin_punto():
    assert "s=AAPL" in feeds.feed_noticias_ticker("AAPL")
