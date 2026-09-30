import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main


def _daily_con_referencias(tmp_path, chile):
    ruta = tmp_path / "daily.json"
    ruta.write_text(json.dumps({"referencias": {"indices": [], "chile": chile}}), encoding="utf-8")
    return ruta


def test_serie_del_banco_central_que_falla_queda_avisada(monkeypatch, tmp_path):
    # Antes el valor anterior se conservaba sin ninguna señal: la UF podía quedar congelada
    # días sin que se notara en la app.
    anterior = {"fuente": "BCCh", "uf": 1.0, "pib": 2.0, "pib_var_12m": 0.1, "pib_periodo": "T1"}
    monkeypatch.setattr(main, "RUTA_DAILY", _daily_con_referencias(tmp_path, anterior))
    monkeypatch.setattr(main.banco_central, "obtener_referencias_chile", lambda: {"fuente": "BCCh", "uf": 3.0})
    monkeypatch.setattr(main.prices, "obtener_cotizacion", lambda t: {"precio": 1.0, "var_dia_pct": 0.0})

    avisos = []
    ref = main.actualizar_referencias(avisos)
    assert ref["chile"]["uf"] == 3.0
    assert ref["chile"]["pib"] == 2.0  # se conserva, como antes
    assert avisos == ["Banco Central: sin dato nuevo de pib (se muestra el anterior)"]


def test_indice_sin_cotizacion_queda_avisado(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "RUTA_DAILY", _daily_con_referencias(tmp_path, {}))
    monkeypatch.setattr(main.banco_central, "obtener_referencias_chile", lambda: {"fuente": "BCCh"})

    def cotizacion(ticker):
        if ticker == "QQQ":
            raise main.prices.FinnhubError("429")
        return {"precio": 1.0, "var_dia_pct": 0.0}

    monkeypatch.setattr(main.prices, "obtener_cotizacion", cotizacion)
    avisos = []
    main.actualizar_referencias(avisos)
    assert avisos == ["Finnhub: sin cotización nueva de QQQ (se muestra la anterior)"]


def test_todo_bien_no_deja_avisos(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "RUTA_DAILY", _daily_con_referencias(tmp_path, {"fuente": "BCCh", "uf": 1.0}))
    monkeypatch.setattr(main.banco_central, "obtener_referencias_chile", lambda: {"fuente": "BCCh", "uf": 2.0})
    monkeypatch.setattr(main.prices, "obtener_cotizacion", lambda t: {"precio": 1.0, "var_dia_pct": 0.0})
    avisos = []
    main.actualizar_referencias(avisos)
    assert avisos == []
