import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import yahoo


class _RespuestaFalsa:
    def __init__(self, contenido: str):
        self._contenido = contenido.encode("utf-8")

    def read(self):
        return self._contenido

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _respuesta_yahoo(timestamps, cierres):
    return json.dumps(
        {"chart": {"result": [{"timestamp": timestamps, "indicators": {"quote": [{"close": cierres}]}}]}}
    )


def test_simbolo_yahoo_normaliza_punto_a_guion():
    assert yahoo._simbolo_yahoo("BRK.B") == "BRK-B"
    assert yahoo._simbolo_yahoo("MSFT") == "MSFT"


def test_descargar_historico_parsea_respuesta(monkeypatch):
    hoy = datetime.datetime.now(datetime.timezone.utc)
    ts1 = int((hoy - datetime.timedelta(days=2)).timestamp())
    ts2 = int((hoy - datetime.timedelta(days=1)).timestamp())
    cuerpo = _respuesta_yahoo([ts1, ts2], [100.5, 101.25])
    monkeypatch.setattr(
        yahoo.urllib.request, "urlopen", lambda req, timeout: _RespuestaFalsa(cuerpo)
    )
    puntos = yahoo.descargar_historico("MSFT", dias=30)
    assert len(puntos) == 2
    assert puntos[0]["valor"] == 100.5
    assert puntos[1]["valor"] == 101.25


def test_descargar_historico_ignora_cierres_null(monkeypatch):
    hoy = datetime.datetime.now(datetime.timezone.utc)
    ts = int(hoy.timestamp())
    cuerpo = _respuesta_yahoo([ts], [None])
    monkeypatch.setattr(
        yahoo.urllib.request, "urlopen", lambda req, timeout: _RespuestaFalsa(cuerpo)
    )
    assert yahoo.descargar_historico("MSFT") == []


def test_descargar_historico_simbolo_no_encontrado_devuelve_vacio(monkeypatch):
    cuerpo = json.dumps({"chart": {"result": None, "error": {"code": "Not Found"}}})
    monkeypatch.setattr(
        yahoo.urllib.request, "urlopen", lambda req, timeout: _RespuestaFalsa(cuerpo)
    )
    assert yahoo.descargar_historico("TICKERFALSO") == []


def test_descargar_historico_error_de_red_devuelve_vacio(monkeypatch):
    def levantar(*args, **kwargs):
        raise yahoo.urllib.error.URLError("sin conexión")

    monkeypatch.setattr(yahoo.urllib.request, "urlopen", levantar)
    assert yahoo.descargar_historico("MSFT") == []
