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
