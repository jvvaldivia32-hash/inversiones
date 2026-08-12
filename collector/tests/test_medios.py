import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from medios import resolver_medio


def test_medio_internacional_conocido():
    r = resolver_medio("reuters.com", "Reuters")
    assert r == {"medio": "Reuters", "grupo": "Reuters", "lean": "centro"}


def test_medio_chileno_conocido_no_inventa_lean_politico():
    r = resolver_medio("ciperchile.cl", "CIPER")
    assert r == {"medio": "CIPER", "grupo": "sin fines de lucro", "lean": "no aplica"}


def test_medio_desconocido_no_inventa_clasificacion():
    r = resolver_medio("un-sitio-random.com", "Sitio Random")
    assert r == {"medio": "Sitio Random", "grupo": "sin-clasificar", "lean": "sin-clasificar"}
