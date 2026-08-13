import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import gemini


class _RespuestaFalsa:
    def __init__(self, contenido: str):
        self._contenido = contenido.encode("utf-8")

    def read(self):
        return self._contenido

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _interaction(texto_json: str) -> str:
    return json.dumps(
        {
            "status": "completed",
            "steps": [
                {"type": "thought"},
                {"type": "model_output", "content": [{"type": "text", "text": texto_json}]},
            ],
        }
    )


# --- _llamar / _es_copia_literal ---


def test_llamar_sin_key_devuelve_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert gemini._llamar("prompt", {}) is None


def test_llamar_parsea_respuesta_completada(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    cuerpo = _interaction('{"ok": true}')
    monkeypatch.setattr(
        gemini.urllib.request, "urlopen", lambda req, timeout: _RespuestaFalsa(cuerpo)
    )
    assert gemini._llamar("prompt", {}) == {"ok": True}


def test_llamar_status_no_completado_devuelve_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    cuerpo = json.dumps({"status": "failed", "steps": []})
    monkeypatch.setattr(
        gemini.urllib.request, "urlopen", lambda req, timeout: _RespuestaFalsa(cuerpo)
    )
    assert gemini._llamar("prompt", {}) is None


def test_llamar_json_invalido_en_texto_devuelve_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    cuerpo = _interaction("esto no es json")
    monkeypatch.setattr(
        gemini.urllib.request, "urlopen", lambda req, timeout: _RespuestaFalsa(cuerpo)
    )
    assert gemini._llamar("prompt", {}) is None


def test_llamar_error_de_red_devuelve_none(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake")

    def levantar(req, timeout):
        raise gemini.urllib.error.URLError("sin conexión")

    monkeypatch.setattr(gemini.urllib.request, "urlopen", levantar)
    assert gemini._llamar("prompt", {}) is None


def test_llamar_timeout_devuelve_none(monkeypatch):
    # TimeoutError no es subclase de URLError (viene de socket) — bug real encontrado en la
    # corrida en vivo: sin este catch, un timeout tumbaba todo el collector en vez de
    # degradar como el resto de sources/.
    monkeypatch.setenv("GEMINI_API_KEY", "fake")

    def levantar(req, timeout):
        raise TimeoutError("se colgó")

    monkeypatch.setattr(gemini.urllib.request, "urlopen", levantar)
    assert gemini._llamar("prompt", {}) is None


def test_es_copia_literal_detecta_racha_larga_compartida():
    original = "El banco central anuncio hoy que mantendra las tasas de interes sin cambios este mes"
    copia = "Segun fuentes, el banco central anuncio hoy que mantendra las tasas de interes sin cambios este mes"
    assert gemini._es_copia_literal(copia, [original]) is True


def test_es_copia_literal_false_si_esta_reescrito():
    original = "El banco central anuncio hoy que mantendra las tasas de interes sin cambios este mes"
    reescrito = "La entidad monetaria decidio no modificar su politica de tasas por ahora"
    assert gemini._es_copia_literal(reescrito, [original]) is False


def test_es_copia_literal_texto_corto_nunca_es_copia():
    assert gemini._es_copia_literal("muy corto", ["cualquier cosa aca"]) is False


# --- agrupar_historias ---


def test_agrupar_historias_lista_vacia_no_llama_api(monkeypatch):
    llamado = []
    monkeypatch.setattr(gemini, "_llamar", lambda *a: llamado.append(1) or None)
    assert gemini.agrupar_historias([]) == []
    assert llamado == []


def test_agrupar_historias_devuelve_grupos_validos(monkeypatch):
    monkeypatch.setattr(
        gemini,
        "_llamar",
        lambda prompt, schema: {
            "historias": [{"titulo_neutral": "Historia A", "indices": [0, 2]}]
        },
    )
    grupos = gemini.agrupar_historias(["t0", "t1", "t2"])
    assert ("Historia A", [0, 2]) in grupos
    # el índice 1 no fue agrupado por Gemini -> queda como historia propia
    assert any(indices == [1] for _, indices in grupos)


def test_agrupar_historias_descarta_indices_fuera_de_rango(monkeypatch):
    monkeypatch.setattr(
        gemini,
        "_llamar",
        lambda prompt, schema: {
            "historias": [{"titulo_neutral": "Historia rara", "indices": [0, 99]}]
        },
    )
    grupos = gemini.agrupar_historias(["t0", "t1"])
    # el 99 se descarta, pero el 0 sigue siendo válido dentro del grupo
    assert ("Historia rara", [0]) in grupos
    assert any(indices == [1] for _, indices in grupos)


def test_agrupar_historias_none_si_llamar_falla(monkeypatch):
    monkeypatch.setattr(gemini, "_llamar", lambda prompt, schema: None)
    assert gemini.agrupar_historias(["t0"]) is None


def test_agrupar_historias_none_si_respuesta_no_tiene_shape_esperado(monkeypatch):
    monkeypatch.setattr(gemini, "_llamar", lambda prompt, schema: {"algo_distinto": []})
    assert gemini.agrupar_historias(["t0"]) is None


# --- reescribir_resumenes ---


def test_reescribir_resumenes_lista_vacia_no_llama_api(monkeypatch):
    llamado = []
    monkeypatch.setattr(gemini, "_llamar", lambda *a: llamado.append(1) or None)
    assert gemini.reescribir_resumenes([]) == []
    assert llamado == []


def test_reescribir_resumenes_todo_vacio_no_llama_api(monkeypatch):
    llamado = []
    monkeypatch.setattr(gemini, "_llamar", lambda *a: llamado.append(1) or None)
    assert gemini.reescribir_resumenes(["", ""]) == [None, None]
    assert llamado == []


def test_reescribir_resumenes_devuelve_por_indice(monkeypatch):
    monkeypatch.setattr(
        gemini,
        "_llamar",
        lambda prompt, schema: {
            "resumenes": [{"indice": 0, "resumen": "Un resumen bien distinto del original"}]
        },
    )
    resultado = gemini.reescribir_resumenes(["texto original aca"])
    assert resultado == ["Un resumen bien distinto del original"]


def test_reescribir_resumenes_descarta_copia_literal(monkeypatch):
    original = "el banco central anuncio hoy que mantendra las tasas de interes sin cambios este mes"
    monkeypatch.setattr(
        gemini,
        "_llamar",
        lambda prompt, schema: {"resumenes": [{"indice": 0, "resumen": original}]},
    )
    resultado = gemini.reescribir_resumenes([original])
    assert resultado == [None]


def test_reescribir_resumenes_none_si_llamar_falla(monkeypatch):
    monkeypatch.setattr(gemini, "_llamar", lambda prompt, schema: None)
    assert gemini.reescribir_resumenes(["algo"]) is None
