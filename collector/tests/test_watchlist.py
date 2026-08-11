import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from watchlist import parse_watchlist


def escribir(tmp_path: Path, contenido: str) -> Path:
    ruta = tmp_path / "watchlist.txt"
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def test_parseo_normal(tmp_path):
    ruta = escribir(tmp_path, "BRK.B\nMCD\nMSFT\nVOO\n")
    assert parse_watchlist(ruta) == ["BRK.B", "MCD", "MSFT", "VOO"]


def test_lineas_en_blanco_se_ignoran(tmp_path):
    ruta = escribir(tmp_path, "MSFT\n\n\nVOO\n")
    assert parse_watchlist(ruta) == ["MSFT", "VOO"]


def test_minusculas_se_normalizan(tmp_path):
    ruta = escribir(tmp_path, "msft\nvoo\n")
    assert parse_watchlist(ruta) == ["MSFT", "VOO"]


def test_ticker_invalido_se_descarta_sin_tumbar_el_resto(tmp_path, capsys):
    ruta = escribir(tmp_path, "MSFT\nesto no es un ticker\nVOO\n")
    assert parse_watchlist(ruta) == ["MSFT", "VOO"]
    assert "línea ignorada" in capsys.readouterr().out


def test_archivo_inexistente_levanta_filenotfounderror(tmp_path):
    ruta = tmp_path / "no-existe.txt"
    with pytest.raises(FileNotFoundError):
        parse_watchlist(ruta)
