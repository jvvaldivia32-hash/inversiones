"""Orquestador del portafolio real de Fintual — corre diario, no cada hora como
main.py: el valor cuota de un fondo mutuo chileno se actualiza una vez al día, pegarle
más seguido es ruido. Ver .github/workflows/fintual_diario.yml.
"""

import datetime
import json
import os
from pathlib import Path

from env import cargar_env
from sources import fintual

RAIZ_REPO = Path(__file__).resolve().parent.parent
RUTA_DAILY = RAIZ_REPO / "data" / "daily.json"


def construir_fintual(ahora: datetime.datetime) -> dict | None:
    """{"goals", "saldo_total", "actualizado"} con datos reales, o None si falló —
    quien llama decide si conserva el valor anterior (mismo criterio de degradación que
    banco_central.py/radar_semanal.py)."""
    email = os.environ.get("FINTUAL_USER_EMAIL", "")
    token = os.environ.get("FINTUAL_USER_TOKEN", "")
    try:
        goals = fintual.obtener_goals(email, token)
    except fintual.FintualError as e:
        print(f"  Fintual no se pudo actualizar ({e})")
        return None

    return {
        "goals": goals,
        "saldo_total": sum(g["saldo"] for g in goals if g["saldo"] is not None),
        "actualizado": ahora.isoformat(),
    }


def main() -> None:
    cargar_env(RAIZ_REPO / ".env")
    ahora = datetime.datetime.now(datetime.timezone.utc)

    for clave in ("FINTUAL_USER_EMAIL", "FINTUAL_USER_TOKEN"):
        estado = "detectada" if os.environ.get(clave) else "no seteada"
        print(f"{clave}: {estado}")

    print("Actualizando portafolio de Fintual...")
    daily = json.loads(RUTA_DAILY.read_text(encoding="utf-8"))
    anterior = daily.get("fintual")

    nuevo = construir_fintual(ahora)
    if nuevo is not None:
        daily["fintual"] = nuevo
        print(f"  {len(nuevo['goals'])} goals, saldo total {nuevo['saldo_total']}")
    elif anterior is not None:
        print("  se conserva el valor anterior")
        daily["fintual"] = anterior
    else:
        print("  sin valor anterior tampoco — daily.json queda sin la clave 'fintual'")

    RUTA_DAILY.write_text(json.dumps(daily, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("data/daily.json actualizado.")


if __name__ == "__main__":
    main()
