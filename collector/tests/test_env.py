import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from env import cargar_env


def test_carga_variables_del_archivo(tmp_path, monkeypatch):
    monkeypatch.delenv("FINNHUB_KEY", raising=False)
    ruta = tmp_path / ".env"
    ruta.write_text("FINNHUB_KEY=abc123\n", encoding="utf-8")
    cargar_env(ruta)
    assert __import__("os").environ["FINNHUB_KEY"] == "abc123"


def test_no_pisa_variable_ya_seteada(tmp_path, monkeypatch):
    monkeypatch.setenv("FINNHUB_KEY", "ya-estaba")
    ruta = tmp_path / ".env"
    ruta.write_text("FINNHUB_KEY=del-archivo\n", encoding="utf-8")
    cargar_env(ruta)
    assert __import__("os").environ["FINNHUB_KEY"] == "ya-estaba"


def test_ignora_comentarios_y_lineas_en_blanco(tmp_path, monkeypatch):
    monkeypatch.delenv("BCCH_USER", raising=False)
    ruta = tmp_path / ".env"
    ruta.write_text("# comentario\n\nBCCH_USER=jose\n", encoding="utf-8")
    cargar_env(ruta)
    assert __import__("os").environ["BCCH_USER"] == "jose"


def test_archivo_inexistente_no_hace_nada(tmp_path):
    cargar_env(tmp_path / "no-existe.env")
