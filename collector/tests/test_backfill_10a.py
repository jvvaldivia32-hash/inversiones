import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import backfill_10a


def test_mezclar_agrega_lo_viejo_sin_tocar_lo_existente():
    existente = [{"ts": "2026-08-11T14:00:00", "valor": 500.0}]
    yahoo = [{"fecha": "2018-03-02", "valor": 93.05}]
    assert backfill_10a.mezclar(existente, yahoo) == [
        {"ts": "2018-03-02T00:00:00", "valor": 93.05},
        {"ts": "2026-08-11T14:00:00", "valor": 500.0},
    ]


def test_mezclar_lo_ya_guardado_gana_ante_choque():
    """Yahoo devuelve cierres diarios a medianoche; si un punto ya guardado cae en el mismo
    ts, se queda el guardado. Sin esto el backfill pisaría el histórico propio del cron con
    el cierre ajustado de Yahoo, que no es el mismo número."""
    existente = [{"ts": "2024-05-06T00:00:00", "valor": 111.11}]
    yahoo = [{"fecha": "2024-05-06", "valor": 999.99}]
    assert backfill_10a.mezclar(existente, yahoo) == [
        {"ts": "2024-05-06T00:00:00", "valor": 111.11}
    ]


def test_mezclar_conserva_la_resolucion_horaria_reciente():
    """El caso que de verdad importa: los últimos 45 días tienen varios puntos por día que
    Yahoo no puede devolver. El backfill no puede colapsarlos a uno."""
    existente = [
        {"ts": "2026-08-11T09:00:00", "valor": 500.0},
        {"ts": "2026-08-11T14:00:00", "valor": 502.0},
        {"ts": "2026-08-11T19:00:00", "valor": 501.0},
    ]
    yahoo = [{"fecha": "2026-08-11", "valor": 501.5}]
    mezclado = backfill_10a.mezclar(existente, yahoo)
    del_dia = [p for p in mezclado if p["ts"].startswith("2026-08-11")]
    assert len(del_dia) == 4  # los 3 horarios propios + el cierre de Yahoo a medianoche
    assert {"ts": "2026-08-11T09:00:00", "valor": 500.0} in del_dia


def test_mezclar_sin_historia_previa():
    yahoo = [{"fecha": "2016-08-11", "valor": 57.2}, {"fecha": "2016-08-12", "valor": 57.9}]
    assert backfill_10a.mezclar([], yahoo) == [
        {"ts": "2016-08-11T00:00:00", "valor": 57.2},
        {"ts": "2016-08-12T00:00:00", "valor": 57.9},
    ]
