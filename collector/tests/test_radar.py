import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import radar

AHORA = datetime.datetime(2026, 8, 13, tzinfo=datetime.timezone.utc)


def _serie_plana(valor: float, dias: int, hasta: datetime.datetime = AHORA) -> list[dict]:
    return [
        {"ts": (hasta - datetime.timedelta(days=i)).date().isoformat(), "valor": valor}
        for i in range(dias)
    ]


def test_computar_castigada_none_si_hay_pocos_puntos():
    serie = _serie_plana(100, 10)
    assert radar.computar_castigada(serie, AHORA) is None


def test_computar_castigada_no_castigada_si_precio_en_el_maximo():
    serie = _serie_plana(100, 300)
    resultado = radar.computar_castigada(serie, AHORA)
    assert resultado["castigada"] is False
    assert resultado["pct_bajo_maximo"] == 0.0
    assert resultado["bajo_ma200"] is False


def test_computar_castigada_true_si_cae_mas_de_15_por_ciento_del_maximo():
    serie = _serie_plana(100, 300)
    # los últimos 10 días el precio se desploma
    for i in range(10):
        serie[i]["valor"] = 80
    resultado = radar.computar_castigada(serie, AHORA)
    assert resultado["castigada"] is True
    assert resultado["pct_bajo_maximo"] == 20.0


def test_computar_castigada_true_si_esta_bajo_la_media_movil_200():
    serie = _serie_plana(100, 300)
    for i in range(60):
        serie[i]["valor"] = 90  # baja pero no lo suficiente para el criterio de 52 semanas
    resultado = radar.computar_castigada(serie, AHORA)
    assert resultado["bajo_ma200"] is True
    assert resultado["castigada"] is True


def test_computar_castigada_none_sin_datos_del_ultimo_anio():
    hace_dos_anios = AHORA - datetime.timedelta(days=800)
    serie = _serie_plana(100, 300, hasta=hace_dos_anios)
    assert radar.computar_castigada(serie, AHORA) is None


def _series_sana(ultimo_ingreso_extra=1, ultimo_margen=10, ultimo_flujo=10):
    # 5 trimestres crecientes en secuencia -> pasa YoY y 3-de-4
    ingresos = [
        {"periodo": f"FY25Q{i}" if i <= 4 else "FY26Q1", "valor": 100 + i * 10}
        for i in range(1, 5)
    ] + [{"periodo": "FY26Q1", "valor": 100 + 4 * 10 + ultimo_ingreso_extra}]
    return {
        "ingresos_musd": ingresos,
        "margen_operativo": [{"periodo": "FY26Q1", "valor": ultimo_margen}],
        "flujo_op_musd": [{"periodo": "FY26Q1", "valor": ultimo_flujo}],
    }


def test_evaluar_sana_none_sin_suficiente_historia():
    series = {"ingresos_musd": [{"periodo": "FY26Q1", "valor": 100}], "margen_operativo": [], "flujo_op_musd": []}
    assert radar.evaluar_sana(series, deuda_patrimonio=0.5, es_banco=False) is None


def test_evaluar_sana_none_sin_deuda_patrimonio_si_no_es_banco():
    assert radar.evaluar_sana(_series_sana(), deuda_patrimonio=None, es_banco=False) is None


def test_evaluar_sana_banco_no_necesita_deuda_patrimonio():
    resultado = radar.evaluar_sana(_series_sana(), deuda_patrimonio=None, es_banco=True)
    assert resultado is not None
    assert resultado["sana"] is True


def test_evaluar_sana_todo_bien_es_sana():
    resultado = radar.evaluar_sana(_series_sana(), deuda_patrimonio=0.3, es_banco=False)
    assert resultado == {"sana": True, "motivos": []}


def test_evaluar_sana_margen_negativo():
    resultado = radar.evaluar_sana(_series_sana(ultimo_margen=-5), deuda_patrimonio=0.3, es_banco=False)
    assert resultado["sana"] is False
    assert "margen operativo negativo" in resultado["motivos"]


def test_evaluar_sana_flujo_operativo_negativo():
    resultado = radar.evaluar_sana(_series_sana(ultimo_flujo=-1), deuda_patrimonio=0.3, es_banco=False)
    assert "flujo operativo negativo" in resultado["motivos"]


def test_evaluar_sana_deuda_patrimonio_alta():
    resultado = radar.evaluar_sana(_series_sana(), deuda_patrimonio=3.0, es_banco=False)
    assert any("deuda/patrimonio" in m for m in resultado["motivos"])


def test_evaluar_sana_ingresos_cayendo_interanual():
    series = _series_sana(ultimo_ingreso_extra=-100)  # último trimestre bien por debajo del de hace un año
    resultado = radar.evaluar_sana(series, deuda_patrimonio=0.3, es_banco=False)
    assert "ingresos cayendo interanual" in resultado["motivos"]


def test_evaluar_sana_pocos_trimestres_positivos():
    ingresos = [
        {"periodo": "FY25Q1", "valor": 100},
        {"periodo": "FY25Q2", "valor": 90},
        {"periodo": "FY25Q3", "valor": 80},
        {"periodo": "FY25Q4", "valor": 70},
        {"periodo": "FY26Q1", "valor": 200},  # sube fuerte YoY, pero cayó 3 trimestres seguidos antes
    ]
    series = {
        "ingresos_musd": ingresos,
        "margen_operativo": [{"periodo": "FY26Q1", "valor": 10}],
        "flujo_op_musd": [{"periodo": "FY26Q1", "valor": 10}],
    }
    resultado = radar.evaluar_sana(series, deuda_patrimonio=0.3, es_banco=False)
    assert any("de los últimos 4 trimestres" in m for m in resultado["motivos"])
