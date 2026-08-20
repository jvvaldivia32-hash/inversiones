import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import paper_aporte_mensual as paper  # noqa: E402

AHORA = datetime.datetime(2026, 9, 1, 6, 0, tzinfo=datetime.timezone.utc)


def test_cargar_archivo_inexistente_bootstrapea_con_5000(tmp_path):
    ruta = tmp_path / "paperinvesting.json"
    estado = paper.cargar(ruta, AHORA)
    assert estado == {
        "fecha_inicio": "2026-09-01",
        "saldo_no_invertido_usd": 5000.0,
        "aportes": [],
        "posiciones": {},
    }


def test_cargar_archivo_existente_no_lo_reinicia(tmp_path):
    ruta = tmp_path / "paperinvesting.json"
    original = {
        "fecha_inicio": "2026-08-20",
        "saldo_no_invertido_usd": 250.0,
        "aportes": [{"fecha": "2026-09-01", "monto_usd": 100.0}],
        "posiciones": {"MSFT": {"acciones": 1.0, "costo_base_usd": 500.0}},
    }
    ruta.write_text(json.dumps(original), encoding="utf-8")
    assert paper.cargar(ruta, AHORA) == original


def test_aportar_suma_100_y_registra_el_aporte():
    estado = paper._estado_inicial("2026-08-20")
    estado = paper.aportar(estado, AHORA)
    assert estado["saldo_no_invertido_usd"] == 5100.0
    assert estado["aportes"] == [{"fecha": "2026-09-01", "monto_usd": 100.0}]


def test_aportar_es_acumulativo_mes_a_mes():
    estado = paper._estado_inicial("2026-08-20")
    estado = paper.aportar(estado, AHORA)
    estado = paper.aportar(estado, datetime.datetime(2026, 10, 1, 6, 0, tzinfo=datetime.timezone.utc))
    assert estado["saldo_no_invertido_usd"] == 5200.0
    assert len(estado["aportes"]) == 2


def test_guardar_y_recargar_da_lo_mismo(tmp_path):
    ruta = tmp_path / "paperinvesting.json"
    estado = paper.aportar(paper._estado_inicial("2026-08-20"), AHORA)
    paper.guardar(ruta, estado)
    assert paper.cargar(ruta, AHORA) == estado
