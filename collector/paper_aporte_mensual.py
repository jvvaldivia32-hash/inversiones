"""Simulador de cartera ficticia ("paper investing") — extra fuera del plan madre, pedido
por José 2026-08-20: partir con $5.000 ficticios y sumar un "sueldo" simulado de $100 el
día 1 de cada mes. Corre mensual, no diario ni horario como el resto del collector — ver
.github/workflows/paper_aporte_mensual.yml. Sin llamadas a APIs externas: es puro cálculo
local sobre data/paperinvesting.json.
"""

import datetime
import json
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parent.parent
RUTA_PAPER = RAIZ_REPO / "data" / "paperinvesting.json"

SALDO_INICIAL_USD = 5000.0
APORTE_MENSUAL_USD = 100.0


def _estado_inicial(fecha: str) -> dict:
    return {
        "fecha_inicio": fecha,
        "saldo_no_invertido_usd": SALDO_INICIAL_USD,
        "aportes": [],
        "posiciones": {},
    }


def cargar(ruta: Path, ahora: datetime.datetime) -> dict:
    """data/paperinvesting.json se sembró a mano con los $5.000 iniciales (mismo criterio
    que watchlist.txt/tesis.json) — este bootstrap es solo defensivo, por si el archivo
    llegara a faltar."""
    if not ruta.exists():
        return _estado_inicial(ahora.date().isoformat())
    return json.loads(ruta.read_text(encoding="utf-8"))


def aportar(estado: dict, ahora: datetime.datetime) -> dict:
    estado["saldo_no_invertido_usd"] += APORTE_MENSUAL_USD
    estado["aportes"].append({"fecha": ahora.date().isoformat(), "monto_usd": APORTE_MENSUAL_USD})
    return estado


def guardar(ruta: Path, estado: dict) -> None:
    ruta.write_text(json.dumps(estado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    ahora = datetime.datetime.now(datetime.timezone.utc)
    estado = cargar(RUTA_PAPER, ahora)
    estado = aportar(estado, ahora)
    guardar(RUTA_PAPER, estado)
    print(f"Aporte de US${APORTE_MENSUAL_USD:.0f} sumado — saldo no invertido: "
          f"US${estado['saldo_no_invertido_usd']:.2f}")


if __name__ == "__main__":
    main()
