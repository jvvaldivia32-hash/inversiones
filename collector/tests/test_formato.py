import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from formato import num, pct


def test_num_usa_puntos_de_miles_y_coma_decimal():
    assert num(1234.56) == "1.234,56"
    assert num(10941.0077, 0) == "10.941"


def test_pct_de_un_dia_plano_no_se_lee_como_caida():
    assert pct(0.0) == "+0,0%"
    assert pct(-0.04) == "+0,0%"  # redondea a cero: mostrarlo como "−0,0%" confunde


def test_pct_conserva_el_signo_real():
    assert pct(-0.2) == "−0,2%"
    assert pct(1.5) == "+1,5%"
