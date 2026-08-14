"""Orquestador de la sección "Amigos" — corre diario, no cada hora como main.py: ni el
precio de un par de tickers ajenos ni un recap de noticias necesitan actualizarse más
seguido que eso. Ver .github/workflows/amigos_diario.yml.

`data/amigos.json` es la config editable (por cada amigo, vía web/api/amigos.ts, sin
clave compartida — el límite real es que la API nunca deja crear un id nuevo, solo editar
uno de los que ya existen). Este script lee esa config, resuelve los datos en vivo, y
escribe el resultado en data/daily.json bajo la clave "amigos" — mismo patrón de
degradación silenciosa que fintual_diario.py: si algo falla para un amigo puntual, se
conserva su valor anterior en vez de dejarlo en blanco."""

import datetime
import json
from pathlib import Path

from env import cargar_env
from sources import amigos

RAIZ_REPO = Path(__file__).resolve().parent.parent
RUTA_AMIGOS = RAIZ_REPO / "data" / "amigos.json"
RUTA_DAILY = RAIZ_REPO / "data" / "daily.json"


def _amigos_anteriores() -> dict[str, dict]:
    daily = json.loads(RUTA_DAILY.read_text(encoding="utf-8"))
    return {a["id"]: a for a in daily.get("amigos", []) if a.get("id")}


def construir_amigo(config: dict, anterior: dict | None, ahora: datetime.datetime) -> dict:
    """{"id", "nombre", "modo", "datos", "actualizado"} con datos reales, o `anterior` si
    algo salió mal — las funciones de sources/amigos.py ya degradan campo por campo
    internamente (un ticker roto no tumba los demás), así que llegar acá con una
    excepción real es el caso raro (ej. FINNHUB_KEY no seteada)."""
    base = {"id": config["id"], "nombre": config.get("nombre", config["id"]), "modo": config.get("modo")}
    try:
        if config.get("modo") == "tickers":
            datos = {"tickers": amigos.obtener_datos_tickers(config.get("tickers") or [])}
        elif config.get("modo") == "palabra_clave":
            palabra = config.get("palabra_clave") or ""
            datos = {
                "palabra_clave": palabra,
                "titulares": amigos.obtener_recap_palabra_clave(palabra),
            }
        else:
            print(f"  {config.get('id')}: modo desconocido, se omite")
            return anterior if anterior else {**base, "datos": {}}
        base["datos"] = datos
        base["actualizado"] = ahora.isoformat()
        return base
    except Exception as e:  # noqa: BLE001 — cualquier cosa rara: degradar, no tumbar la corrida
        print(f"  {config.get('id')}: no se pudo actualizar ({e})")
        return anterior if anterior else {**base, "datos": {}}


def main() -> None:
    cargar_env(RAIZ_REPO / ".env")
    ahora = datetime.datetime.now(datetime.timezone.utc)

    if not RUTA_AMIGOS.exists():
        print("data/amigos.json no existe todavía — nada que hacer.")
        return

    config_amigos = json.loads(RUTA_AMIGOS.read_text(encoding="utf-8"))
    anteriores = _amigos_anteriores()

    print(f"Actualizando {len(config_amigos)} amigo(s)...")
    resultado = []
    for config in config_amigos:
        anterior = anteriores.get(config.get("id"))
        amigo = construir_amigo(config, anterior, ahora)
        resultado.append(amigo)
        print(f"  {amigo['nombre']}: ok")

    daily = json.loads(RUTA_DAILY.read_text(encoding="utf-8"))
    daily["amigos"] = resultado
    RUTA_DAILY.write_text(json.dumps(daily, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("data/daily.json actualizado con la sección 'amigos'.")


if __name__ == "__main__":
    main()
