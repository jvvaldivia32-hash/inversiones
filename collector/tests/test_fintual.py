import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import fintual


def test_obtener_goals_sin_credenciales():
    with pytest.raises(fintual.FintualError, match="FINTUAL_USER_EMAIL"):
        fintual.obtener_goals("", "")


def test_obtener_goals_parsea_shape_real(monkeypatch):
    # Shape real confirmado en vivo contra la API — GET /goals con X-User-Email/X-User-Token.
    monkeypatch.setattr(
        fintual,
        "_request",
        lambda ruta, email, token: {
            "data": [
                {"id": "24", "type": "goal", "attributes": {"name": "Mi Casita", "nav": 666.0}},
                {"id": "31", "type": "goal", "attributes": {"name": "Jubilación", "nav": 1500.5}},
            ]
        },
    )
    resultado = fintual.obtener_goals("jose@example.com", "fake-token")
    assert resultado == [
        {"id": "24", "nombre": "Mi Casita", "saldo": 666.0},
        {"id": "31", "nombre": "Jubilación", "saldo": 1500.5},
    ]


def test_obtener_goals_lista_vacia(monkeypatch):
    monkeypatch.setattr(fintual, "_request", lambda ruta, email, token: {"data": []})
    assert fintual.obtener_goals("jose@example.com", "fake-token") == []


def test_request_envia_los_headers_correctos(monkeypatch):
    capturado = {}

    class _RespuestaFalsa:
        def read(self):
            return b'{"data": []}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _urlopen_falso(req, timeout):
        capturado["headers"] = dict(req.headers)
        capturado["url"] = req.full_url
        return _RespuestaFalsa()

    monkeypatch.setattr(fintual.urllib.request, "urlopen", _urlopen_falso)
    fintual._request("/goals", "jose@example.com", "el-token")
    assert capturado["headers"]["X-user-email"] == "jose@example.com"
    assert capturado["headers"]["X-user-token"] == "el-token"
    assert capturado["url"] == "https://fintual.cl/api/goals"


def test_request_error_http(monkeypatch):
    def _urlopen_falso(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(fintual.urllib.request, "urlopen", _urlopen_falso)
    with pytest.raises(fintual.FintualError, match="401"):
        fintual._request("/goals", "jose@example.com", "token-vencido")


def test_request_timeout_no_reventado(monkeypatch):
    def _urlopen_falso(req, timeout):
        raise TimeoutError("se colgó")

    monkeypatch.setattr(fintual.urllib.request, "urlopen", _urlopen_falso)
    with pytest.raises(fintual.FintualError):
        fintual._request("/goals", "jose@example.com", "token")
