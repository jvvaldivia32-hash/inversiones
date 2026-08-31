"""Resumen de cada mañana por Telegram: dónde quedó todo antes de que abra el mercado.

Lo dispara el recolector horario (`enviar_si_toca()`, llamado desde collector/main.py), no
un cron propio. Ver la nota de VENTANA abajo: el cron propio existía y GitHub lo botaba.
No le pide nada a ninguna API — todo sale de `data/daily.json`, que el recolector acaba de
dejar escrito.

Igual que las alertas, esto informa y no aconseja: precios, variaciones y los titulares que
ya están en la app, sin ninguna lectura de qué conviene hacer (regla dura de CLAUDE.md).
Los extractos de noticias son los que Gemini ya reescribió, con link a la fuente — nunca
texto copiado del original.
"""

import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from env import cargar_env
from formato import num, pct
from sources import telegram

RAIZ_REPO = Path(__file__).resolve().parent.parent
RUTA_DAILY = RAIZ_REPO / "data" / "daily.json"
RUTA_ESTADO = RAIZ_REPO / "data" / "resumen_enviado.json"

# Ventana, en hora de Chile, dentro de la cual el recolector manda el resumen del día: el
# primer run que caiga acá adentro y no haya mandado nada todavía, lo manda.
#
# Por qué así y no un cron propio a las 07:38: GitHub bota y encola los eventos `schedule`
# de este repo desde el 26-08-2026 (ver CLAUDE.md punto 2). Ese cron llegó a disparar a las
# 11:26 y 11:44 de Chile —después de que abre el mercado— y el 31-08 no disparó en todo el
# día. Colgarlo del recolector no da una hora exacta, pero le da muchos más intentos: en los
# 8 días medidos (24 al 31 de agosto), *todos* tuvieron al menos un run acá adentro, incluido
# el 27 que tuvo 2 runs en las 24 horas. Los mismos días, el cron propio llegó más tarde o no
# llegó.
#
# 07:00 y no antes: el cierre de ayer ya está firme desde la noche, pero un "buenos días" a
# las 2 de la mañana no es un resumen de la mañana. 12:00 y no después, por lo mismo al
# revés — pasado mediodía deja de ser el mensaje que se pidió y es mejor no mandarlo.
HORA_DESDE = 7
HORA_HASTA = 12
ZONA_CHILE = ZoneInfo("America/Santiago")

# Cuántos titulares de cada bloque entran. Más que esto y el mensaje deja de leerse de un
# vistazo en el celular, que es todo el punto del resumen.
TITULARES_POR_BLOQUE = 2

# Desde qué antigüedad de `daily.json` el resumen avisa que el dato está viejo. El
# recolector corre cada hora *todos los días* (fin de semana incluido: Finnhub devuelve el
# último cierre), así que a las 11:38 UTC el snapshot normal tiene menos de una hora. Tres
# horas ya no es "el mercado está cerrado", es "el recolector no está dejando dato nuevo" —
# que fue exactamente lo que pasó el 26-27 de agosto de 2026, cuando GitHub botó los eventos
# `schedule` y el mensaje de la mañana hubiera llegado igual, idéntico y sin avisar nada.
HORAS_PARA_AVISAR = 3

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _fecha_larga(dia: datetime.date) -> str:
    return f"{dia.day} de {MESES[dia.month - 1]}"


def _antiguedad_horas(daily: dict, ahora: datetime.datetime) -> float | None:
    """Cuántas horas hace que el recolector escribió `daily.json`. None si no se puede saber."""
    generado = daily.get("generado")
    if not generado:
        return None
    try:
        cuando = datetime.datetime.fromisoformat(generado)
    except ValueError:
        return None
    if cuando.tzinfo is None:  # snapshots viejos, escritos sin huso
        cuando = cuando.replace(tzinfo=datetime.timezone.utc)
    return (ahora - cuando).total_seconds() / 3600


def _aviso_dato_viejo(daily: dict, ahora: datetime.datetime) -> str | None:
    """Avisa arriba de todo cuando los precios de abajo no son de esta mañana.

    Sin esto, un recolector caído produce un resumen idéntico al normal: mismos precios de
    siempre, ninguna señal. El aviso dice *qué* pasa con el dato, no qué hacer con él.
    """
    horas = _antiguedad_horas(daily, ahora)
    if horas is None:
        return "⚠️ <b>No se pudo leer cuándo se actualizó el dato.</b> Los precios de abajo pueden estar viejos."
    if horas < HORAS_PARA_AVISAR:
        return None

    if horas < 48:
        cuanto = f"{round(horas)} horas"
    else:
        cuanto = f"{round(horas / 24)} días"
    return (
        f"⚠️ <b>Estos precios son de hace {cuanto}.</b>\n"
        "El recolector no está dejando dato nuevo — lo de abajo es el último snapshot que "
        "quedó guardado, no el cierre de ayer."
    )


def _linea_ticker(t: dict) -> str:
    var = t.get("var_dia_pct")
    variacion = pct(var) if var is not None else "s/d"
    return f"• <b>{telegram.escapar(t['ticker'])}</b>  US$ {num(t['precio'])}  ({variacion})"


def _bloque_titulares(titulo: str, historias: list[dict]) -> str | None:
    lineas = []
    for h in historias[:TITULARES_POR_BLOQUE]:
        articulos = h.get("articulos") or []
        texto = telegram.escapar(h["titulo_neutral"])
        if articulos and articulos[0].get("url"):
            url = telegram.escapar(articulos[0]["url"])
            lineas.append(f'• <a href="{url}">{texto}</a>')
        else:
            lineas.append(f"• {texto}")
    if not lineas:
        return None
    return f"<b>{titulo}</b>\n" + "\n".join(lineas)


def construir(daily: dict, ahora: datetime.datetime) -> str:
    partes = [f"<b>Buenos días · {_fecha_larga(ahora.date())}</b>"]

    # Arriba de todo y no al pie: si el dato está viejo, eso cambia cómo se lee cada número
    # que viene después.
    aviso = _aviso_dato_viejo(daily, ahora)
    if aviso:
        partes.append(aviso)

    # Ordenadas por cuánto se movieron, no alfabéticamente: lo que se movió es lo que
    # querés ver primero cuando abrís el mensaje en el celular.
    posiciones = [p for p in daily.get("posiciones", []) if p.get("precio") is not None]
    posiciones.sort(key=lambda p: abs(p.get("var_dia_pct") or 0), reverse=True)
    if posiciones:
        partes.append("<b>Tus tickers</b>\n" + "\n".join(_linea_ticker(p) for p in posiciones))

    # VOO está en la watchlist *y* es índice de referencia: sin este filtro sale dos veces
    # en el mismo mensaje, con el mismo precio.
    ya_listados = {p["ticker"] for p in posiciones}
    indices = [
        i for i in daily.get("referencias", {}).get("indices", []) if i["ticker"] not in ya_listados
    ]
    if indices:
        partes.append("<b>Mercado</b>\n" + "\n".join(_linea_ticker(i) for i in indices))

    chile = daily.get("referencias", {}).get("chile", {})
    if chile:
        campos = []
        if chile.get("ipsa") is not None:
            campos.append(f"IPSA {num(chile['ipsa'], 0)}")
        if chile.get("dolar") is not None:
            campos.append(f"dólar ${num(chile['dolar'], 0)}")
        if chile.get("uf") is not None:
            campos.append(f"UF ${num(chile['uf'], 0)}")
        if chile.get("tpm") is not None:
            campos.append(f"TPM {num(chile['tpm'], 2)}%")
        if chile.get("ipc_12m") is not None:
            campos.append(f"IPC 12m {num(chile['ipc_12m'], 1)}%")
        if campos:
            partes.append("<b>Chile</b>\n" + " · ".join(campos))

    bloques = daily.get("bloques", {})
    for titulo, clave in (("Mundo", "mundo"), ("Chile — noticias", "chile")):
        bloque = _bloque_titulares(titulo, bloques.get(clave, []))
        if bloque:
            partes.append(bloque)

    url_app = os.environ.get("APP_URL")
    if url_app:
        partes.append(f'<a href="{telegram.escapar(url_app)}">Ver todo en la app</a>')

    return "\n\n".join(partes)


def _dia_chile(ahora: datetime.datetime) -> str:
    """El día según Chile, no según UTC: es el día del que habla el mensaje."""
    return ahora.astimezone(ZONA_CHILE).strftime("%Y-%m-%d")


def en_ventana(ahora: datetime.datetime) -> bool:
    return HORA_DESDE <= ahora.astimezone(ZONA_CHILE).hour < HORA_HASTA


def cargar_estado(ruta: Path = RUTA_ESTADO) -> dict:
    try:
        estado = json.loads(ruta.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"ultimo_envio": None}
    return {"ultimo_envio": estado.get("ultimo_envio")}


def guardar_estado(dia: str, ruta: Path = RUTA_ESTADO) -> None:
    ruta.write_text(
        json.dumps({"ultimo_envio": dia}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def enviar_si_toca(
    daily: dict, ahora: datetime.datetime, ruta_estado: Path = RUTA_ESTADO
) -> bool:
    """Punto de entrada desde main.py: manda el resumen si es la mañana y todavía no salió.

    El recolector corre muchas veces al día, así que esto se llama muchas veces y casi
    siempre no hace nada. El que manda es el primer run que caiga en la ventana; el estado
    en `data/resumen_enviado.json` —que daily.yml commitea junto al snapshot, igual que
    `alertas_enviadas.json`— evita que los siguientes repitan el mensaje.
    """
    if not telegram.configurado():
        print("  Telegram sin configurar, no se manda resumen")
        return False

    local = ahora.astimezone(ZONA_CHILE)
    if not en_ventana(ahora):
        print(
            f"  fuera de la ventana del resumen: {local:%H:%M} de Chile "
            f"(ventana {HORA_DESDE:02d}:00–{HORA_HASTA:02d}:00)"
        )
        return False

    dia = _dia_chile(ahora)
    if cargar_estado(ruta_estado)["ultimo_envio"] == dia:
        print(f"  el resumen de hoy ({dia}) ya salió")
        return False

    mensaje = construir(daily, local)
    if not telegram.enviar(mensaje):
        # Igual que las alertas: si el envío falló no se marca el día, así el próximo run
        # dentro de la ventana reintenta en vez de dar por mandado algo que nunca llegó.
        print("  el resumen no se pudo enviar, se reintenta en el próximo run")
        return False

    guardar_estado(dia, ruta_estado)
    print(f"  resumen de la mañana enviado ({len(mensaje)} caracteres, {local:%H:%M} de Chile)")
    return True


def main() -> None:
    cargar_env(RAIZ_REPO / ".env")

    if not telegram.configurado():
        print("Telegram sin configurar (falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID).")
        return

    daily = json.loads(RUTA_DAILY.read_text(encoding="utf-8"))
    generado = daily.get("generado")
    print(f"daily.json generado: {generado}")

    # A propósito no mira ni la ventana ni el estado del día: este camino es el botón
    # manual del workflow, o sea un "mándamelo ahora" explícito. Tampoco marca el día como
    # enviado, así que no le saca el turno al automático.
    mensaje = construir(daily, datetime.datetime.now(ZONA_CHILE))
    print(f"Enviando resumen ({len(mensaje)} caracteres)...")
    if telegram.enviar(mensaje):
        print("Resumen enviado.")


if __name__ == "__main__":
    main()
