import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import alertas
from sources import prices


def _no_deberia_llamarse(ticker):
    raise AssertionError("no debería pedirle el precio a Finnhub, ya vino por watchlist")


def _mov(ticker, var, precio=100.0, **extra):
    return {"ticker": ticker, "nombre": ticker, "precio": precio, "var_dia_pct": var, **extra}


def test_detectar_ignora_movimientos_chicos():
    estado = {"fecha": None, "avisados": {}}
    encontradas, nuevo = alertas.detectar([_mov("MSFT", 4.9)], estado, "2026-08-27")
    assert encontradas == []
    assert nuevo["avisados"] == {}


def test_detectar_toma_subidas_y_bajadas():
    estado = {"fecha": None, "avisados": {}}
    encontradas, nuevo = alertas.detectar(
        [_mov("MSFT", 5.1), _mov("PEP", -7.3), _mov("KO", 0.4)], estado, "2026-08-27"
    )
    assert [a["ticker"] for a in encontradas] == ["MSFT", "PEP"]
    assert nuevo == {"fecha": "2026-08-27", "avisados": {"MSFT": 5.1, "PEP": -7.3}}


def test_detectar_no_repite_el_mismo_dia():
    estado = {"fecha": "2026-08-27", "avisados": {"MSFT": 5.1}}
    encontradas, _ = alertas.detectar([_mov("MSFT", 6.4)], estado, "2026-08-27")
    assert encontradas == []


def test_detectar_reavisa_si_se_movio_otro_umbral_entero():
    estado = {"fecha": "2026-08-27", "avisados": {"MSFT": 5.1}}
    encontradas, nuevo = alertas.detectar([_mov("MSFT", 10.2)], estado, "2026-08-27")
    assert [a["ticker"] for a in encontradas] == ["MSFT"]
    assert nuevo["avisados"]["MSFT"] == 10.2


def test_detectar_reavisa_al_cambiar_de_dia():
    estado = {"fecha": "2026-08-26", "avisados": {"MSFT": 5.1}}
    encontradas, nuevo = alertas.detectar([_mov("MSFT", 5.5)], estado, "2026-08-27")
    assert [a["ticker"] for a in encontradas] == ["MSFT"]
    assert nuevo["fecha"] == "2026-08-27"


def test_detectar_tolera_variacion_ausente():
    # Finnhub a veces no manda `dp`; sin esto la comparación revienta con TypeError.
    encontradas, _ = alertas.detectar([_mov("MSFT", None)], {"fecha": None, "avisados": {}}, "2026-08-27")
    assert encontradas == []


def test_hoy_usa_el_dia_de_mercado_no_utc():
    # 00:30 UTC del 28 todavía es la sesión del 27 en Nueva York.
    ahora = datetime.datetime(2026, 8, 28, 0, 30, tzinfo=datetime.timezone.utc)
    assert alertas._hoy(ahora) == "2026-08-27"


def test_formatear_incluye_ticker_variacion_precio_y_noticia():
    texto = alertas.formatear(
        [
            _mov(
                "PEP",
                -6.25,
                precio=1234.5,
                origen="Radar",
                noticia={"titular": "Pepsi & Co recorta guidance", "medio": "Reuters", "url": "https://x.test/a"},
            )
        ]
    )
    assert "PEP" in texto
    assert "−6,2%" in texto          # menos tipográfico y coma decimal
    assert "US$ 1.234,50" in texto   # miles con punto
    assert "Radar" in texto
    assert "Pepsi &amp; Co" in texto  # el & se escapa o Telegram rechaza el HTML
    assert "https://x.test/a" in texto


def test_formatear_sin_noticia_no_deja_bloque_vacio():
    texto = alertas.formatear([_mov("MSFT", 5.5)])
    assert "<i>" not in texto


def test_recolectar_movimientos_junta_watchlist_y_radar(monkeypatch):
    monkeypatch.setattr(
        prices, "obtener_cotizacion", lambda t: {"precio": 50.0, "var_dia_pct": -9.0, "cierre_anterior": 55.0}
    )
    daily = {
        "posiciones": [{"ticker": "MSFT", "precio": 500.0, "var_dia_pct": 1.0, "noticias": []}],
        "radar": {"candidatos": [{"ticker": "PEP", "nombre": "PepsiCo"}]},
    }
    movs = alertas.recolectar_movimientos(daily)
    assert [(m["ticker"], m["origen"]) for m in movs] == [("MSFT", "watchlist"), ("PEP", "Radar")]


def test_recolectar_movimientos_no_duplica_un_ticker_en_ambas_listas(monkeypatch):
    monkeypatch.setattr(prices, "obtener_cotizacion", _no_deberia_llamarse)
    daily = {
        "posiciones": [{"ticker": "PEP", "precio": 100.0, "var_dia_pct": 1.0, "noticias": []}],
        "radar": {"candidatos": [{"ticker": "PEP", "nombre": "PepsiCo"}]},
    }
    movs = alertas.recolectar_movimientos(daily)
    assert [m["ticker"] for m in movs] == ["PEP"]  # y sin gastar una llamada a Finnhub


def test_recolectar_movimientos_sigue_si_finnhub_falla(monkeypatch):
    def explota(ticker):
        raise prices.FinnhubError("429")

    monkeypatch.setattr(prices, "obtener_cotizacion", explota)
    daily = {
        "posiciones": [{"ticker": "MSFT", "precio": 500.0, "var_dia_pct": 1.0, "noticias": []}],
        "radar": {"candidatos": [{"ticker": "PEP", "nombre": "PepsiCo"}]},
    }
    assert [m["ticker"] for m in alertas.recolectar_movimientos(daily)] == ["MSFT"]


def test_estado_ida_y_vuelta(tmp_path):
    ruta = tmp_path / "alertas_enviadas.json"
    alertas.guardar_estado({"fecha": "2026-08-27", "avisados": {"MSFT": 5.1}}, ruta)
    assert alertas.cargar_estado(ruta) == {"fecha": "2026-08-27", "avisados": {"MSFT": 5.1}}


def test_cargar_estado_sin_archivo_o_corrupto(tmp_path):
    assert alertas.cargar_estado(tmp_path / "no-existe.json") == {"fecha": None, "avisados": {}}
    roto = tmp_path / "roto.json"
    roto.write_text("{no es json", encoding="utf-8")
    assert alertas.cargar_estado(roto) == {"fecha": None, "avisados": {}}


def test_revisar_no_guarda_estado_si_el_envio_falla(monkeypatch, tmp_path):
    # Si el aviso no llegó al celular, el próximo run tiene que reintentar.
    monkeypatch.setattr(alertas.telegram, "configurado", lambda: True)
    monkeypatch.setattr(alertas.telegram, "enviar", lambda texto: False)
    ruta = tmp_path / "estado.json"
    daily = {"posiciones": [{"ticker": "MSFT", "precio": 500.0, "var_dia_pct": 9.0, "noticias": []}]}

    assert alertas.revisar(daily, datetime.datetime.now(datetime.timezone.utc), ruta) == []
    assert not ruta.exists()


def test_revisar_guarda_estado_cuando_envia(monkeypatch, tmp_path):
    monkeypatch.setattr(alertas.telegram, "configurado", lambda: True)
    monkeypatch.setattr(alertas.telegram, "enviar", lambda texto: True)
    ruta = tmp_path / "estado.json"
    daily = {"posiciones": [{"ticker": "MSFT", "precio": 500.0, "var_dia_pct": 9.0, "noticias": []}]}

    enviadas = alertas.revisar(daily, datetime.datetime.now(datetime.timezone.utc), ruta)
    assert [a["ticker"] for a in enviadas] == ["MSFT"]
    assert json.loads(ruta.read_text(encoding="utf-8"))["avisados"] == {"MSFT": 9.0}


def test_revisar_no_hace_nada_sin_telegram_configurado(monkeypatch, tmp_path):
    monkeypatch.setattr(alertas.telegram, "configurado", lambda: False)
    daily = {"posiciones": [{"ticker": "MSFT", "precio": 500.0, "var_dia_pct": 9.0, "noticias": []}]}
    assert alertas.revisar(daily, datetime.datetime.now(datetime.timezone.utc), tmp_path / "e.json") == []
