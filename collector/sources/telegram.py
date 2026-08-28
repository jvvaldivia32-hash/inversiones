import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.telegram.org"

# Telegram corta los mensajes en 4096 caracteres. Se recorta antes de mandar para que un
# resumen largo llegue mocho en vez de rebotar entero con un 400.
LARGO_MAXIMO = 4096


class TelegramError(Exception):
    pass


def configurado() -> bool:
    """¿Están las dos variables que hacen falta para mandar?

    Que falten no es un error: el recolector tiene que seguir funcionando igual para quien
    corra el repo sin bot (o para una corrida local). Los llamadores usan esto para saltarse
    el envío en silencio en vez de tumbar la corrida entera por un aviso.
    """
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def escapar(texto: str) -> str:
    """Escapa lo que Telegram interpretaría como HTML dentro del texto propio.

    Los nombres de empresa y los titulares vienen de fuentes externas y traen `&`, `<` y
    comillas raras — sin esto, un titular con un `<` deja el mensaje sin enviar.
    """
    return html.escape(texto, quote=False)


_TAG = re.compile(r"<(/?)([a-z]+)[^>]*>")


def _cerrar_tags(texto: str) -> str:
    """Cierra las etiquetas que quedaron abiertas al cortar. Telegram rechaza el mensaje
    entero con un 400 si ve un `<b>` sin su `</b>`."""
    abiertos = []
    for cierra, tag in _TAG.findall(texto):
        if cierra:
            if abiertos and abiertos[-1] == tag:
                abiertos.pop()
        else:
            abiertos.append(tag)
    return texto + "".join(f"</{t}>" for t in reversed(abiertos))


def _sin_fragmento_final(texto: str) -> str:
    """Saca una etiqueta o una entidad partida al medio (`<a hre`, `&am`) al final del corte."""
    for abre, cierra in (("<", ">"), ("&", ";")):
        i = texto.rfind(abre)
        if i != -1 and cierra not in texto[i:]:
            texto = texto[:i]
    return texto


def recortar(texto: str, maximo: int = LARGO_MAXIMO) -> str:
    """Corta un mensaje largo dejándolo como HTML válido.

    Cortar a lo bruto en el carácter 4095 parte una etiqueta o una entidad al medio, y
    Telegram rebota el mensaje con el mismo 400 que este recorte quiere evitar. Se corta
    en el borde de un bloque si se puede, y si no, se cierra lo que quedó abierto.
    """
    if len(texto) <= maximo:
        return texto

    # Margen para el "…" y para las etiquetas de cierre que puede haber que agregar.
    corte = texto[: maximo - 40]
    # Borde de bloque si se puede, si no de línea, y recién ahí a lo bruto: un corte a mitad
    # de línea deja un "US$ 712,0" colgando que se lee como dato roto.
    borde = max(corte.rfind("\n\n"), corte.rfind("\n"))
    corte = corte[:borde] if borde > maximo // 2 else _sin_fragmento_final(corte)
    return _cerrar_tags(corte) + "\n…"


def enviar(texto: str) -> bool:
    """Manda un mensaje al chat configurado. Devuelve si se envió.

    Nunca levanta excepción hacia el recolector: un aviso que no sale no puede costar la
    corrida de precios del día. Loguea y sigue.
    """
    if not configurado():
        print("  Telegram sin configurar (falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID)")
        return False

    texto = recortar(texto)

    url = f"{BASE_URL}/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
    datos = urllib.parse.urlencode(
        {
            "chat_id": os.environ["TELEGRAM_CHAT_ID"],
            "text": texto,
            "parse_mode": "HTML",
            # Sin esto Telegram pega una tarjeta gigante del primer link y el mensaje queda
            # ilegible en el celular.
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")

    try:
        with urllib.request.urlopen(url, data=datos, timeout=10) as resp:
            respuesta = json.loads(resp.read().decode("utf-8"))
        if not respuesta.get("ok"):
            print(f"  Telegram rechazó el mensaje: {respuesta.get('description')}")
            return False
        return True
    except urllib.error.HTTPError as e:
        # El cuerpo del 400 dice *por qué* (chat_id malo, HTML roto); sin leerlo el error
        # es inútil para depurar.
        detalle = e.read().decode("utf-8", "replace")[:200]
        print(f"  Telegram respondió {e.code}: {detalle}")
        return False
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        # TimeoutError no es subclase de URLError (viene de socket, no de urllib) — mismo
        # gotcha ya visto en sources/gemini.py y sources/prices.py.
        print(f"  Telegram no respondió: {e}")
        return False
