"""Orquestador de la sección "Amigos" — corre diario, no cada hora como main.py: ni el
precio de un par de tickers ajenos ni un recap de noticias necesitan actualizarse más
seguido que eso. Ver .github/workflows/amigos_diario.yml.

`data/amigos.json` es la config editable (por cada amigo, vía web/api/amigos.ts, sin
clave compartida — el límite real es que la API nunca deja crear un id nuevo, solo editar
uno de los que ya existen). Cada amigo arma una lista libre de "seguimientos" (mezcla de
tickers y palabras clave). Este script resuelve los datos en vivo de cada seguimiento y
escribe el resultado en data/daily.json bajo la clave "amigos" — mismo patrón de
degradación silenciosa que fintual_diario.py: si algo falla para un seguimiento puntual,
se conserva su valor anterior en vez de dejarlo en blanco."""

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


def _dato_anterior(anterior_amigo: dict | None, tipo: str, valor: str) -> dict | None:
    if not anterior_amigo:
        return None
    for s in anterior_amigo.get("seguimientos", []):
        if s.get("tipo") == tipo and s.get("valor") == valor:
            return s.get("datos")
    return None


def construir_seguimiento(item: dict, anterior_amigo: dict | None) -> dict:
    tipo = item.get("tipo")
    valor = item.get("valor", "")
    anterior = _dato_anterior(anterior_amigo, tipo, valor)

    if tipo == "ticker":
        dato = amigos.obtener_dato_ticker(valor)
        datos = dato if dato is not None else (anterior or None)
    elif tipo == "palabra_clave":
        titulares = amigos.obtener_recap_palabra_clave(valor)
        datos = {"titulares": titulares} if titulares else (anterior or {"titulares": []})
    else:
        datos = anterior

    return {"tipo": tipo, "valor": valor, "datos": datos}


def construir_amigo(config: dict, anterior: dict | None, ahora: datetime.datetime) -> dict:
    """{"id", "nombre", "seguimientos", "actualizado"} — cada seguimiento degrada
    independiente (un ticker roto o una búsqueda sin resultados no tumba a los demás)."""
    seguimientos = [
        construir_seguimiento(item, anterior)
        for item in (config.get("seguimientos") or [])[: amigos.MAX_SEGUIMIENTOS]
    ]
    return {
        "id": config["id"],
        "nombre": config.get("nombre", config["id"]),
        # Solo pasa a daily.json si ya viene en la config (provisionada a mano) — nunca se
        # inventa una acá. Ver Amigos.tsx: gate de contraseña por amigo, cliente-side a
        # propósito, no es autenticación real (decisión explícita 2026-08-15).
        "clave": config.get("clave"),
        "seguimientos": seguimientos,
        "actualizado": ahora.isoformat(),
    }


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
        print(f"  {amigo['nombre']}: {len(amigo['seguimientos'])} seguimiento(s)")

    daily = json.loads(RUTA_DAILY.read_text(encoding="utf-8"))
    daily["amigos"] = resultado
    RUTA_DAILY.write_text(json.dumps(daily, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("data/daily.json actualizado con la sección 'amigos'.")


if __name__ == "__main__":
    main()
