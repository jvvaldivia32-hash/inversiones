import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import banco_central


class _RespuestaFalsa:
    def __init__(self, contenido: str):
        self._contenido = contenido.encode("latin-1")

    def read(self):
        return self._contenido

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _respuesta_json(codigo, obs):
    import json

    return json.dumps({"Codigo": codigo, "Series": {"Obs": obs}})


def test_obtener_valor_sin_token_devuelve_none(monkeypatch):
    monkeypatch.delenv("BCCH_API_KEY", raising=False)
    assert banco_central._obtener_valor("F073.UFF.PRE.Z.D") is None


def test_obtener_valor_toma_el_ultimo_ok(monkeypatch):
    monkeypatch.setenv("BCCH_API_KEY", "fake")
    obs = [
        {"indexDateString": "10-08-2026", "value": "39200.0", "statusCode": "OK"},
        {"indexDateString": "11-08-2026", "value": "NaN", "statusCode": "ND"},
        {"indexDateString": "12-08-2026", "value": "NaN", "statusCode": "ND"},
    ]
    cuerpo = _respuesta_json(0, obs)
    monkeypatch.setattr(
        banco_central.urllib.request, "urlopen", lambda url, timeout: _RespuestaFalsa(cuerpo)
    )
    assert banco_central._obtener_valor("F073.UFF.PRE.Z.D") == 39200.0


def test_obtener_valor_todo_nd_devuelve_none(monkeypatch):
    monkeypatch.setenv("BCCH_API_KEY", "fake")
    obs = [{"indexDateString": "12-08-2026", "value": "NaN", "statusCode": "ND"}]
    cuerpo = _respuesta_json(0, obs)
    monkeypatch.setattr(
        banco_central.urllib.request, "urlopen", lambda url, timeout: _RespuestaFalsa(cuerpo)
    )
    assert banco_central._obtener_valor("F073.UFF.PRE.Z.D") is None


def test_obtener_valor_codigo_de_error_devuelve_none(monkeypatch):
    monkeypatch.setenv("BCCH_API_KEY", "fake")
    cuerpo = _respuesta_json(-1, [])
    monkeypatch.setattr(
        banco_central.urllib.request, "urlopen", lambda url, timeout: _RespuestaFalsa(cuerpo)
    )
    assert banco_central._obtener_valor("codigo-invalido") is None


def test_obtener_valor_error_de_red_devuelve_none(monkeypatch):
    monkeypatch.setenv("BCCH_API_KEY", "fake")

    def levantar(url, timeout):
        raise banco_central.urllib.error.URLError("sin conexión")

    monkeypatch.setattr(banco_central.urllib.request, "urlopen", levantar)
    assert banco_central._obtener_valor("F073.UFF.PRE.Z.D") is None


def test_obtener_referencias_chile_omite_campos_fallidos(monkeypatch):
    def falso_obtener_valor(codigo, dias=10):
        return 100.0 if codigo == banco_central.SERIES["uf"] else None

    monkeypatch.setattr(banco_central, "_obtener_valor", falso_obtener_valor)
    resultado = banco_central.obtener_referencias_chile()
    assert resultado["uf"] == 100.0
    assert resultado["fuente"] == "Banco Central de Chile"
    assert "dolar" not in resultado
    assert "tpm" not in resultado


def test_obtener_referencias_chile_pide_pib_con_ventana_trimestral(monkeypatch):
    # PIB es trimestral (una obs cada ~91 días) — con la ventana default de 45 días
    # quedaría fuera de rango casi siempre, mismo bug que ya pasó con IPC/IPSA mensuales.
    llamadas = {}

    def falso_obtener_valor(codigo, dias=10):
        llamadas[codigo] = dias
        return 1.0

    monkeypatch.setattr(banco_central, "_obtener_valor", falso_obtener_valor)
    banco_central.obtener_referencias_chile()
    assert llamadas[banco_central.SERIES["pib"]] == 120
    assert llamadas[banco_central.SERIES["desocupacion"]] == 120
    assert llamadas[banco_central.SERIES["uf"]] == 45
