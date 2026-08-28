import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tesis

AHORA = datetime.datetime(2026, 8, 13, tzinfo=datetime.timezone.utc)


# --- calcular_semaforo ---


def test_semaforo_mayor_es_mejor_verde():
    assert tesis.calcular_semaforo(45, umbral_verde=40, umbral_rojo=30, direccion="mayor_es_mejor") == "verde"


def test_semaforo_mayor_es_mejor_ambar():
    assert tesis.calcular_semaforo(35, umbral_verde=40, umbral_rojo=30, direccion="mayor_es_mejor") == "ambar"


def test_semaforo_mayor_es_mejor_rojo():
    assert tesis.calcular_semaforo(25, umbral_verde=40, umbral_rojo=30, direccion="mayor_es_mejor") == "rojo"


def test_semaforo_mayor_es_mejor_limites_inclusivos():
    assert tesis.calcular_semaforo(40, umbral_verde=40, umbral_rojo=30, direccion="mayor_es_mejor") == "verde"
    assert tesis.calcular_semaforo(30, umbral_verde=40, umbral_rojo=30, direccion="mayor_es_mejor") == "ambar"


def test_semaforo_menor_es_mejor_verde():
    assert tesis.calcular_semaforo(0.5, umbral_verde=1, umbral_rojo=2, direccion="menor_es_mejor") == "verde"


def test_semaforo_menor_es_mejor_ambar():
    assert tesis.calcular_semaforo(1.5, umbral_verde=1, umbral_rojo=2, direccion="menor_es_mejor") == "ambar"


def test_semaforo_menor_es_mejor_rojo():
    assert tesis.calcular_semaforo(3, umbral_verde=1, umbral_rojo=2, direccion="menor_es_mejor") == "rojo"


# --- revisar_tesis ---


def _tesis(metrica_tipo, metrica_campo, direccion="mayor_es_mejor", umbral_verde=40, umbral_rojo=30):
    return {
        "metrica_tipo": metrica_tipo,
        "metrica_campo": metrica_campo,
        "umbral_verde": umbral_verde,
        "umbral_rojo": umbral_rojo,
        "direccion": direccion,
    }


def test_revisar_tesis_fundamental_ok():
    t = _tesis("fundamental", "margen_operativo")
    fund = {
        "periodo": "FY26Q4",
        "fuente_url": "https://sec.gov/x",
        "series": {"margen_operativo": [{"periodo": "FY26Q3", "valor": 40}, {"periodo": "FY26Q4", "valor": 45}]},
    }
    resultado = tesis.revisar_tesis(t, AHORA, fund, None)
    assert resultado["valor"] == 45
    assert resultado["periodo"] == "FY26Q4"
    assert resultado["semaforo"] == "verde"
    assert resultado["fuente_url"] == "https://sec.gov/x"
    assert resultado["extraido_por"] == "xbrl"
    assert resultado["cita_textual"] == ""


def test_revisar_tesis_fundamental_none_sin_fundamentales():
    t = _tesis("fundamental", "margen_operativo")
    assert tesis.revisar_tesis(t, AHORA, None, None) is None


def test_revisar_tesis_fundamental_none_si_el_campo_no_existe():
    t = _tesis("fundamental", "eps_non_gaap")
    fund = {"periodo": "FY26Q4", "fuente_url": "x", "series": {"eps_non_gaap": []}}
    assert tesis.revisar_tesis(t, AHORA, fund, None) is None


def test_revisar_tesis_segmento_ok():
    t = _tesis("segmento", "Azure and other cloud services", umbral_verde=40, umbral_rojo=30)
    seg = {
        "segmentos": [{"nombre": "Azure and other cloud services", "var_pct": 43, "cita": "increased 43%"}],
        "fuente_url": "https://sec.gov/8k",
    }
    fund = {"periodo": "FY26Q4", "fuente_url": "x", "series": {}}
    resultado = tesis.revisar_tesis(t, AHORA, fund, seg)
    assert resultado["valor"] == 43
    assert resultado["semaforo"] == "verde"
    assert resultado["fuente_url"] == "https://sec.gov/8k"
    assert resultado["cita_textual"] == "increased 43%"
    assert resultado["extraido_por"] == "segmento"
    assert resultado["periodo"] == "FY26Q4"


def test_revisar_tesis_segmento_none_si_no_esta_este_trimestre():
    t = _tesis("segmento", "Azure and other cloud services")
    seg = {"segmentos": [{"nombre": "Otro segmento", "var_pct": 5, "cita": "x"}], "fuente_url": "y"}
    assert tesis.revisar_tesis(t, AHORA, None, seg) is None


def test_revisar_tesis_segmento_none_sin_segmentos():
    t = _tesis("segmento", "Azure and other cloud services")
    assert tesis.revisar_tesis(t, AHORA, None, None) is None


# --- fusionar(): dos escritores sobre data/tesis.json (el recolector y web/api/tesis.ts) ---


def _lectura(valor, semaforo, fecha="2026-08-28", periodo="FY26Q4"):
    return {
        "periodo": periodo,
        "fecha_reporte": fecha,
        "valor": valor,
        "semaforo": semaforo,
        "fuente_url": "https://sec.gov/8k",
        "cita_textual": "",
        "extraido_por": "segmento",
    }


def _guardada(id_="t1", estado="activa", lecturas=None):
    t = _tesis("segmento", "Azure and other cloud services")
    t["id"] = id_
    t["texto"] = "Azure crece por encima del resto de la nube."
    t["estado"] = estado
    t["lecturas"] = lecturas or []
    return t


def test_fusionar_agrega_la_lectura_nueva():
    base = [_guardada()]
    revisada = [_guardada(lecturas=[_lectura(43, "verde")])]
    salida = tesis.fusionar(base, revisada)
    assert len(salida[0]["lecturas"]) == 1
    assert salida[0]["lecturas"][0]["valor"] == 43
    assert salida[0]["estado"] == "activa"


def test_fusionar_no_duplica_la_misma_lectura():
    ya = _lectura(43, "verde")
    base = [_guardada(lecturas=[ya])]
    revisada = [_guardada(lecturas=[dict(ya)])]
    assert tesis.fusionar(base, revisada)[0]["lecturas"] == [ya]


def test_fusionar_marca_rota_con_lectura_roja():
    base = [_guardada()]
    revisada = [_guardada(lecturas=[_lectura(12, "rojo")])]
    assert tesis.fusionar(base, revisada)[0]["estado"] == "rota"


def test_fusionar_conserva_la_tesis_que_solo_existe_en_el_repo():
    """La escribió el usuario desde la web mientras el recolector corría: no se pierde."""
    base = [_guardada(), _guardada(id_="nueva")]
    revisada = [_guardada(lecturas=[_lectura(43, "verde")])]
    salida = tesis.fusionar(base, revisada)
    assert [t["id"] for t in salida] == ["t1", "nueva"]
    assert salida[1]["lecturas"] == []


def test_fusionar_no_revive_la_tesis_que_el_usuario_borro():
    revisada = [_guardada(lecturas=[_lectura(43, "verde")])]
    assert tesis.fusionar([], revisada) == []


def test_fusionar_no_toca_una_tesis_ya_cerrada():
    base = [_guardada(estado="cerrada")]
    revisada = [_guardada(lecturas=[_lectura(12, "rojo")])]
    salida = tesis.fusionar(base, revisada)
    assert salida[0]["estado"] == "cerrada"
    assert salida[0]["lecturas"] == []


def test_fusionar_nunca_copia_los_umbrales_de_la_corrida():
    """Regla dura: una tesis es inmutable. Si `revisada` viene con otros umbrales
    (corrida vieja, archivo desincronizado), manda siempre lo que está en el repo."""
    base = [_guardada()]
    vieja = _guardada(lecturas=[_lectura(43, "verde")])
    vieja["umbral_verde"] = 999
    vieja["texto"] = "otro texto"
    salida = tesis.fusionar(base, vieja and [vieja])
    assert salida[0]["umbral_verde"] == base[0]["umbral_verde"]
    assert salida[0]["texto"] == base[0]["texto"]


def test_fusionar_no_muta_la_lista_de_entrada():
    base = [_guardada()]
    tesis.fusionar(base, [_guardada(lecturas=[_lectura(43, "verde")])])
    assert base[0]["lecturas"] == []
