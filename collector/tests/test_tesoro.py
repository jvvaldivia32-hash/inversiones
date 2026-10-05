import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sources import tesoro

CSV = '''Date,"1 Mo","1 Yr","2 Yr"
10/03/2025,4.10,3.64,3.57
10/02/2025,4.12,3.66,3.58
10/01/2025,4.13,,3.60
'''


def test_parsea_columna_1_anio_y_salta_vacios():
    assert tesoro._parsear(CSV) == [
        (datetime.date(2025, 10, 3), 3.64),
        (datetime.date(2025, 10, 2), 3.66),
    ]


def test_toma_el_ultimo_dato_en_o_antes_de_la_fecha(monkeypatch):
    monkeypatch.setattr(tesoro, "_descargar_anio", lambda anio: tesoro._parsear(CSV))
    # domingo 5-oct: el último publicado es el viernes 3
    assert tesoro.tasa_1a(datetime.date(2025, 10, 5)) == (datetime.date(2025, 10, 3), 3.64)


def test_comienzo_de_enero_busca_en_el_anio_anterior(monkeypatch):
    pedidos = []

    def descargar(anio):
        pedidos.append(anio)
        return tesoro._parsear(CSV) if anio == 2025 else []

    monkeypatch.setattr(tesoro, "_descargar_anio", descargar)
    assert tesoro.tasa_1a(datetime.date(2026, 1, 1))[1] == 3.64
    assert pedidos == [2026, 2025]


def test_sin_datos_levanta_error(monkeypatch):
    monkeypatch.setattr(tesoro, "_descargar_anio", lambda anio: [])
    with pytest.raises(tesoro.TesoroError):
        tesoro.tasa_1a(datetime.date(2025, 10, 5))
