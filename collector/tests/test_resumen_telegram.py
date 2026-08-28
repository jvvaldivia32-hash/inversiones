import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import resumen_telegram
from formato import num, pct
from sources import telegram

DAILY = {
    "posiciones": [
        {"ticker": "MSFT", "precio": 504.91, "var_dia_pct": 0.12, "noticias": []},
        {"ticker": "BRK.B", "precio": 1234.5, "var_dia_pct": -3.4, "noticias": []},
    ],
    "referencias": {
        "indices": [{"ticker": "VOO", "precio": 704.2, "var_dia_pct": 0.0256}],
        "chile": {"ipsa": 10941.0, "uf": 40868.5, "dolar": 918.42, "tpm": 4.5, "ipc_12m": 3.52},
    },
    "bloques": {
        "mundo": [
            {"titulo_neutral": "Titular de prueba", "articulos": [{"url": "https://x.test/n"}]},
            {"titulo_neutral": "Segundo titular", "articulos": []},
            {"titulo_neutral": "Tercero que no debería salir", "articulos": []},
        ],
        "chile": [],
    },
}

HOY = datetime.date(2026, 8, 27)


def test_num_formato_chileno():
    assert num(1234.5) == "1.234,50"
    assert num(10941.0, 0) == "10.941"


def test_pct_lleva_signo_explicito():
    assert pct(3.42) == "+3,4%"
    assert pct(-3.42) == "−3,4%"


def test_construir_arma_las_secciones():
    texto = resumen_telegram.construir(DAILY, HOY)
    assert "27 de agosto" in texto
    assert "Tus tickers" in texto
    assert "Mercado" in texto
    assert "IPSA 10.941" in texto
    assert "dólar $918" in texto
    assert "https://x.test/n" in texto


def test_construir_ordena_por_cuanto_se_movio():
    # BRK.B (−3,4%) va antes que MSFT (+0,12%) aunque sea la segunda de la lista.
    texto = resumen_telegram.construir(DAILY, HOY)
    assert texto.index("BRK.B") < texto.index("MSFT")


def test_construir_corta_los_titulares():
    texto = resumen_telegram.construir(DAILY, HOY)
    assert "Tercero que no debería salir" not in texto


def test_construir_omite_secciones_vacias():
    texto = resumen_telegram.construir({"posiciones": [], "referencias": {}, "bloques": {}}, HOY)
    assert "Tus tickers" not in texto
    assert "Mercado" not in texto
    assert "27 de agosto" in texto


def test_construir_agrega_link_a_la_app_solo_si_hay_url(monkeypatch):
    monkeypatch.delenv("APP_URL", raising=False)
    assert "Ver todo en la app" not in resumen_telegram.construir(DAILY, HOY)
    monkeypatch.setenv("APP_URL", "https://app.test")
    assert "https://app.test" in resumen_telegram.construir(DAILY, HOY)


def test_construir_entra_en_un_mensaje_de_telegram():
    assert len(resumen_telegram.construir(DAILY, HOY)) <= telegram.LARGO_MAXIMO


def test_construir_tolera_ticker_sin_variacion():
    daily = {"posiciones": [{"ticker": "MSFT", "precio": 500.0, "var_dia_pct": None}]}
    assert "s/d" in resumen_telegram.construir(daily, HOY)


def test_telegram_configurado(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert telegram.configurado() is False
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    assert telegram.configurado() is False  # falta el chat
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "y")
    assert telegram.configurado() is True


def test_telegram_no_envia_sin_configurar(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert telegram.enviar("hola") is False


def test_telegram_escapa_html():
    assert telegram.escapar("Pepsi & <b>Co</b>") == "Pepsi &amp; &lt;b&gt;Co&lt;/b&gt;"
