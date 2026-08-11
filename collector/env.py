import os
from pathlib import Path


def cargar_env(ruta: Path) -> None:
    """Carga variables desde un archivo .env (KEY=VALUE por línea) hacia os.environ.

    No pisa una variable que ya esté seteada en el entorno real — así una corrida en
    GitHub Actions (que inyecta los secrets como variables de entorno reales) se comporta
    igual con o sin este archivo presente.
    """
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        clave = clave.strip()
        valor = valor.strip().strip('"').strip("'")
        os.environ.setdefault(clave, valor)
