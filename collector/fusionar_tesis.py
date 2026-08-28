"""Fusiona las lecturas de tesis de una corrida sobre la versión de origin/main.

Lo corre `.github/workflows/daily.yml` justo antes de commitear, después de
`git reset --hard origin/main`: en ese punto `data/tesis.json` es lo último que
escribió la web y el argumento es lo que dejó el recolector. Ver tesis.fusionar()
para por qué manda el archivo del repo y no el de la corrida.

    python collector/fusionar_tesis.py /tmp/xxx/tesis.json
"""

import json
import sys
from pathlib import Path

import tesis

RUTA_TESIS = Path(__file__).resolve().parent.parent / "data" / "tesis.json"


def _leer(ruta: Path) -> list[dict]:
    if not ruta.exists():
        return []
    return json.loads(ruta.read_text(encoding="utf-8"))


def main(ruta_revisada: str) -> int:
    base = _leer(RUTA_TESIS)
    revisada = _leer(Path(ruta_revisada))

    if not base and not RUTA_TESIS.exists():
        print("tesis: no hay data/tesis.json, nada que fusionar")
        return 0

    fusionada = tesis.fusionar(base, revisada)
    antes = sum(len(t.get("lecturas", [])) for t in base)
    despues = sum(len(t.get("lecturas", [])) for t in fusionada)

    RUTA_TESIS.write_text(
        json.dumps(fusionada, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"tesis: {len(fusionada)} tesis, {despues - antes} lectura(s) nueva(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
