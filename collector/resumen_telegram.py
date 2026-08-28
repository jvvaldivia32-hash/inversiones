"""Resumen de cada mañana por Telegram: dónde quedó todo antes de que abra el mercado.

Corre en su propio cron (.github/workflows/resumen_telegram.yml) y no le pide nada a
ninguna API: todo sale de `data/daily.json`, que el recolector horario ya dejó escrito.

Igual que las alertas, esto informa y no aconseja: precios, variaciones y los titulares que
ya están en la app, sin ninguna lectura de qué conviene hacer (regla dura de CLAUDE.md).
Los extractos de noticias son los que Gemini ya reescribió, con link a la fuente — nunca
texto copiado del original.
"""

import datetime
import json
import os
from pathlib import Path

from env import cargar_env
from formato import num, pct
from sources import telegram

RAIZ_REPO = Path(__file__).resolve().parent.parent
RUTA_DAILY = RAIZ_REPO / "data" / "daily.json"

# Cuántos titulares de cada bloque entran. Más que esto y el mensaje deja de leerse de un
# vistazo en el celular, que es todo el punto del resumen.
TITULARES_POR_BLOQUE = 2

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _fecha_larga(dia: datetime.date) -> str:
    return f"{dia.day} de {MESES[dia.month - 1]}"


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


def construir(daily: dict, hoy: datetime.date) -> str:
    partes = [f"<b>Buenos días · {_fecha_larga(hoy)}</b>"]

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


def main() -> None:
    cargar_env(RAIZ_REPO / ".env")

    if not telegram.configurado():
        print("Telegram sin configurar (falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID).")
        return

    daily = json.loads(RUTA_DAILY.read_text(encoding="utf-8"))
    generado = daily.get("generado")
    print(f"daily.json generado: {generado}")

    mensaje = construir(daily, datetime.date.today())
    print(f"Enviando resumen ({len(mensaje)} caracteres)...")
    if telegram.enviar(mensaje):
        print("Resumen enviado.")


if __name__ == "__main__":
    main()
