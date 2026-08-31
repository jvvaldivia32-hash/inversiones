import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import resumen_telegram
from formato import num, pct
from sources import telegram

DAILY = {
    "generado": "2026-08-27T11:17:04+00:00",
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

# 11:38 UTC, la hora del cron: el snapshot de las 11:17 tiene 21 minutos, lo normal.
AHORA = datetime.datetime(2026, 8, 27, 11, 38, tzinfo=datetime.timezone.utc)


def test_num_formato_chileno():
    assert num(1234.5) == "1.234,50"
    assert num(10941.0, 0) == "10.941"


def test_pct_lleva_signo_explicito():
    assert pct(3.42) == "+3,4%"
    assert pct(-3.42) == "−3,4%"


def test_construir_arma_las_secciones():
    texto = resumen_telegram.construir(DAILY, AHORA)
    assert "27 de agosto" in texto
    assert "Tus tickers" in texto
    assert "Mercado" in texto
    assert "IPSA 10.941" in texto
    assert "dólar $918" in texto
    assert "https://x.test/n" in texto


def test_construir_ordena_por_cuanto_se_movio():
    # BRK.B (−3,4%) va antes que MSFT (+0,12%) aunque sea la segunda de la lista.
    texto = resumen_telegram.construir(DAILY, AHORA)
    assert texto.index("BRK.B") < texto.index("MSFT")


def test_construir_corta_los_titulares():
    texto = resumen_telegram.construir(DAILY, AHORA)
    assert "Tercero que no debería salir" not in texto


def test_construir_omite_secciones_vacias():
    texto = resumen_telegram.construir({"posiciones": [], "referencias": {}, "bloques": {}}, AHORA)
    assert "Tus tickers" not in texto
    assert "Mercado" not in texto
    assert "27 de agosto" in texto


def test_construir_agrega_link_a_la_app_solo_si_hay_url(monkeypatch):
    monkeypatch.delenv("APP_URL", raising=False)
    assert "Ver todo en la app" not in resumen_telegram.construir(DAILY, AHORA)
    monkeypatch.setenv("APP_URL", "https://app.test")
    assert "https://app.test" in resumen_telegram.construir(DAILY, AHORA)


def test_construir_entra_en_un_mensaje_de_telegram():
    assert len(resumen_telegram.construir(DAILY, AHORA)) <= telegram.LARGO_MAXIMO


def test_construir_tolera_ticker_sin_variacion():
    daily = {"posiciones": [{"ticker": "MSFT", "precio": 500.0, "var_dia_pct": None}]}
    assert "s/d" in resumen_telegram.construir(daily, AHORA)


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


def test_recortar_deja_pasar_un_mensaje_normal():
    assert telegram.recortar("<b>corto</b>") == "<b>corto</b>"


def test_recortar_corta_en_el_borde_de_un_bloque():
    bloque = "<b>Tus tickers</b>\n" + "\n".join(f"• MSFT {i}" for i in range(20))
    largo = "\n\n".join([bloque] * 40)
    recortado = telegram.recortar(largo)
    assert len(recortado) <= telegram.LARGO_MAXIMO
    assert recortado.endswith("…")
    # Nada de etiquetas partidas ni abiertas: si no, Telegram rebota con un 400.
    assert recortado.count("<b>") == recortado.count("</b>")


def test_recortar_cierra_una_etiqueta_partida_al_medio():
    # Un solo bloque gigante: no hay borde donde cortar, hay que cerrar a mano.
    largo = '<b>Titular</b>\n<a href="https://ejemplo.test/nota">' + "x" * 6000 + "</a>"
    recortado = telegram.recortar(largo)
    assert len(recortado) <= telegram.LARGO_MAXIMO
    assert recortado.count("<a ") == recortado.count("</a>")
    assert not recortado.rstrip("…\n").endswith("<a")


def test_recortar_no_deja_una_entidad_partida():
    largo = "<b>x</b>\n" + "y" * 4080 + "&amp;" * 10
    recortado = telegram.recortar(largo)
    assert len(recortado) <= telegram.LARGO_MAXIMO
    assert "&am" not in recortado.replace("&amp;", "")


def test_no_avisa_nada_con_dato_fresco():
    assert "⚠️" not in resumen_telegram.construir(DAILY, AHORA)


def test_avisa_cuando_el_dato_esta_viejo():
    # El recolector caído produce un resumen idéntico al normal si nadie mira `generado`.
    tarde = AHORA + datetime.timedelta(days=2)
    texto = resumen_telegram.construir(DAILY, tarde)
    assert "hace 2 días" in texto
    # El aviso va arriba de todo: cambia cómo se lee cada número que viene después.
    assert texto.index("⚠️") < texto.index("Tus tickers")


def test_avisa_en_horas_cuando_es_menos_de_dos_dias():
    texto = resumen_telegram.construir(DAILY, AHORA + datetime.timedelta(hours=5))
    assert "hace 5 horas" in texto


def test_no_avisa_por_el_hueco_normal_entre_corridas():
    # El recolector corre a :17 y el resumen sale a :38 — dos horas de gap sigue siendo sano.
    assert "⚠️" not in resumen_telegram.construir(DAILY, AHORA + datetime.timedelta(hours=2))


def test_avisa_si_no_se_puede_saber_cuando_se_genero():
    for daily in ({**DAILY, "generado": None}, {**DAILY, "generado": "vaya uno a saber"}):
        texto = resumen_telegram.construir(daily, AHORA)
        assert "No se pudo leer cuándo se actualizó" in texto


def test_antiguedad_tolera_un_generado_sin_huso():
    daily = {**DAILY, "generado": "2026-08-27T09:38:00"}
    assert resumen_telegram._antiguedad_horas(daily, AHORA) == 2.0


# --- El resumen colgado del recolector (enviar_si_toca) ---------------------------------
#
# El cron propio se sacó porque GitHub lo botaba; ahora lo dispara el recolector horario y
# la ventana + el archivo de estado son lo que evita que mande el mensaje 12 veces al día.

# 14:06 UTC = 10:06 de Chile en invierno: dentro de la ventana. Es la hora real de un run
# del recolector del 31-08-2026, el día que el cron viejo no disparó nunca.
EN_VENTANA = datetime.datetime(2026, 8, 31, 14, 6, tzinfo=datetime.timezone.utc)


def _configurar_telegram(monkeypatch, enviado):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr(telegram, "enviar", lambda texto: enviado.append(texto) or True)


def test_ventana_va_de_las_7_a_las_12_de_chile():
    def utc(hora, minuto=0):
        return datetime.datetime(2026, 8, 31, hora, minuto, tzinfo=datetime.timezone.utc)

    assert not resumen_telegram.en_ventana(utc(10, 59))  # 06:59 CL, todavía de madrugada
    assert resumen_telegram.en_ventana(utc(11, 0))       # 07:00 CL, abre la ventana
    assert resumen_telegram.en_ventana(EN_VENTANA)       # 10:06 CL
    assert resumen_telegram.en_ventana(utc(15, 59))      # 11:59 CL
    assert not resumen_telegram.en_ventana(utc(16, 0))   # 12:00 CL, ya es mediodía


def test_la_ventana_se_corre_sola_con_el_horario_de_verano():
    # En enero Chile está en UTC-3, así que las mismas 11:00 UTC son las 08:00 y no las
    # 07:00. La ventana se define en hora local justamente para no tener que tocarla.
    verano = datetime.datetime(2026, 1, 15, 9, 30, tzinfo=datetime.timezone.utc)
    assert verano.astimezone(resumen_telegram.ZONA_CHILE).hour == 6
    assert not resumen_telegram.en_ventana(verano)


def test_envia_dentro_de_la_ventana_y_marca_el_dia(tmp_path, monkeypatch):
    enviado = []
    _configurar_telegram(monkeypatch, enviado)
    estado = tmp_path / "resumen_enviado.json"

    assert resumen_telegram.enviar_si_toca(DAILY, EN_VENTANA, estado) is True
    assert len(enviado) == 1
    assert "Buenos días" in enviado[0]
    assert resumen_telegram.cargar_estado(estado)["ultimo_envio"] == "2026-08-31"


def test_no_repite_el_resumen_en_el_mismo_dia(tmp_path, monkeypatch):
    enviado = []
    _configurar_telegram(monkeypatch, enviado)
    estado = tmp_path / "resumen_enviado.json"

    resumen_telegram.enviar_si_toca(DAILY, EN_VENTANA, estado)
    # El recolector vuelve a correr una hora después, todavía dentro de la ventana.
    otra_vez = EN_VENTANA + datetime.timedelta(hours=1)
    assert resumen_telegram.enviar_si_toca(DAILY, otra_vez, estado) is False
    assert len(enviado) == 1


def test_vuelve_a_enviar_al_dia_siguiente(tmp_path, monkeypatch):
    enviado = []
    _configurar_telegram(monkeypatch, enviado)
    estado = tmp_path / "resumen_enviado.json"

    resumen_telegram.enviar_si_toca(DAILY, EN_VENTANA, estado)
    assert resumen_telegram.enviar_si_toca(DAILY, EN_VENTANA + datetime.timedelta(days=1), estado)
    assert len(enviado) == 2


def test_no_envia_fuera_de_la_ventana(tmp_path, monkeypatch):
    enviado = []
    _configurar_telegram(monkeypatch, enviado)
    estado = tmp_path / "resumen_enviado.json"

    # 05:45 UTC = 01:45 de Chile: un run real del 31-08, pero nadie quiere un "buenos días"
    # a esa hora.
    madrugada = datetime.datetime(2026, 8, 31, 5, 45, tzinfo=datetime.timezone.utc)
    assert resumen_telegram.enviar_si_toca(DAILY, madrugada, estado) is False
    assert enviado == []
    assert not estado.exists()


def test_no_marca_el_dia_si_el_envio_falla(tmp_path, monkeypatch):
    # Mismo criterio que las alertas: si Telegram no recibió, el próximo run reintenta en
    # vez de dar por mandado algo que nunca llegó al celular.
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr(telegram, "enviar", lambda texto: False)
    estado = tmp_path / "resumen_enviado.json"

    assert resumen_telegram.enviar_si_toca(DAILY, EN_VENTANA, estado) is False
    assert resumen_telegram.cargar_estado(estado)["ultimo_envio"] is None


def test_no_envia_sin_telegram_configurado(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    estado = tmp_path / "resumen_enviado.json"

    assert resumen_telegram.enviar_si_toca(DAILY, EN_VENTANA, estado) is False
    assert not estado.exists()


def test_estado_ilegible_no_bloquea_el_envio(tmp_path, monkeypatch):
    enviado = []
    _configurar_telegram(monkeypatch, enviado)
    estado = tmp_path / "resumen_enviado.json"
    estado.write_text("{ esto no es json", encoding="utf-8")

    assert resumen_telegram.enviar_si_toca(DAILY, EN_VENTANA, estado) is True


def test_el_encabezado_usa_el_dia_de_chile(tmp_path, monkeypatch):
    # 31-08 a las 23:30 de Chile es el 01-09 en UTC. El mensaje habla del día de Chile.
    # (Queda fuera de la ventana; se prueba construir() directo, que es lo que la arma.)
    enviado = []
    _configurar_telegram(monkeypatch, enviado)
    tarde_en_chile = datetime.datetime(2026, 9, 1, 3, 30, tzinfo=datetime.timezone.utc)
    local = tarde_en_chile.astimezone(resumen_telegram.ZONA_CHILE)
    assert "31 de agosto" in resumen_telegram.construir(DAILY, local)
