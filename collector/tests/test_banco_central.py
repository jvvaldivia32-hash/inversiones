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


def test_obtener_valor_timeout_en_la_lectura_devuelve_none(monkeypatch):
    # Un timeout a mitad de la lectura llega como TimeoutError pelado, no como URLError —
    # y main.py no envuelve esta llamada: sin atraparlo tumbaba la corrida entera.
    monkeypatch.setenv("BCCH_API_KEY", "fake")

    def levantar(url, timeout):
        raise TimeoutError("The read operation timed out")

    monkeypatch.setattr(banco_central.urllib.request, "urlopen", levantar)
    assert banco_central._obtener_valor("F073.UFF.PRE.Z.D") is None


def _falsas_observaciones(por_codigo):
    import datetime

    def falso(codigo, dias):
        return [
            (datetime.datetime.strptime(f, "%d-%m-%Y").date(), v)
            for f, v in por_codigo.get(codigo, [])
        ]

    return falso


def test_obtener_referencias_chile_omite_campos_fallidos(monkeypatch):
    series = {banco_central.SERIES["uf"]: [("12-08-2026", 100.0)]}
    monkeypatch.setattr(banco_central, "_obtener_observaciones", _falsas_observaciones(series))
    resultado = banco_central.obtener_referencias_chile()
    assert resultado == {"fuente": "Banco Central de Chile", "uf": 100.0}


def test_pib_variacion_contra_el_mismo_trimestre_del_anio_anterior(monkeypatch):
    # Datos reales del Banco Central: T2 2026 vs T2 2025 da -0,19%, el "-0,2% anual" que
    # publicó el Banco Central. Contra el trimestre anterior (T1 2026) daría +0,32%, que
    # mezcla estacionalidad con crecimiento — por eso se compara con el año anterior.
    series = {
        banco_central.SERIES["pib"]: [
            ("01-04-2025", 53309.877468848),
            ("01-07-2025", 51876.344987102),
            ("01-10-2025", 57246.764686601),
            ("01-01-2026", 53040.1206256171),
            ("01-04-2026", 53210.5539973709),
        ]
    }
    monkeypatch.setattr(banco_central, "_obtener_observaciones", _falsas_observaciones(series))
    r = banco_central.obtener_referencias_chile()
    assert r["pib"] == 53210.5539973709
    assert r["pib_periodo"] == "T2 2026"
    assert round(r["pib_var_12m"], 2) == -0.19


def test_pib_sin_el_trimestre_del_anio_anterior_no_inventa_variacion(monkeypatch):
    series = {banco_central.SERIES["pib"]: [("01-01-2026", 1.0), ("01-04-2026", 2.0)]}
    monkeypatch.setattr(banco_central, "_obtener_observaciones", _falsas_observaciones(series))
    r = banco_central.obtener_referencias_chile()
    assert r["pib"] == 2.0
    assert "pib_var_12m" not in r


def test_desocupacion_trae_el_trimestre_movil_que_termina_en_el_mes(monkeypatch):
    series = {banco_central.SERIES["desocupacion"]: [("01-07-2026", 9.53)]}
    monkeypatch.setattr(banco_central, "_obtener_observaciones", _falsas_observaciones(series))
    r = banco_central.obtener_referencias_chile()
    assert r["desocupacion"] == 9.53
    assert r["desocupacion_periodo"] == "may–jul 2026"


def test_periodo_trimestre_movil_cruza_el_anio():
    import datetime

    # ene 2026 = trimestre nov 2025–ene 2026; se rotula con el año del mes final.
    assert banco_central._periodo_trimestre_movil(datetime.date(2026, 1, 1)) == "nov–ene 2026"
