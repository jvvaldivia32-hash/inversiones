import datetime

EstadoSemaforo = str  # "verde" | "ambar" | "rojo"


def calcular_semaforo(
    valor: float, umbral_verde: float, umbral_rojo: float, direccion: str
) -> EstadoSemaforo:
    """Sección 4 de docs/spec-rastreador-tesis.md, sin cambios — el semáforo nunca
    recomienda comprar/vender, solo dice si lo que el usuario predijo está pasando."""
    if direccion == "menor_es_mejor":
        if valor <= umbral_verde:
            return "verde"
        if valor <= umbral_rojo:
            return "ambar"
        return "rojo"

    if valor >= umbral_verde:
        return "verde"
    if valor >= umbral_rojo:
        return "ambar"
    return "rojo"


def revisar_tesis(
    tesis: dict,
    ahora: datetime.datetime,
    fundamentales: dict | None,
    segmentos_resultado: dict | None,
) -> dict | None:
    """Lectura nueva para `tesis` (shape de Tesis en web/src/types.ts) buscando el valor
    en lo que Fase 4 (fundamentales) o Fase 5 (segmentos) YA extrajeron esta corrida — no
    vuelve a pegarle a EDGAR/Gemini, el dato (y su cita, si es de un segmento) ya existen.
    None si la métrica no aparece en los datos de esta corrida — no inventa una lectura
    ni recicla la anterior con una fecha nueva."""
    periodo = fundamentales.get("periodo", "") if fundamentales else ""

    if tesis["metrica_tipo"] == "fundamental":
        if not fundamentales:
            return None
        serie = fundamentales.get("series", {}).get(tesis["metrica_campo"])
        if not serie:
            return None
        ultimo = serie[-1]
        return {
            "periodo": ultimo["periodo"],
            "fecha_reporte": ahora.date().isoformat(),
            "valor": ultimo["valor"],
            "semaforo": calcular_semaforo(
                ultimo["valor"], tesis["umbral_verde"], tesis["umbral_rojo"], tesis["direccion"]
            ),
            "fuente_url": fundamentales["fuente_url"],
            "cita_textual": "",
            "extraido_por": "xbrl",
        }

    if tesis["metrica_tipo"] == "segmento":
        if not segmentos_resultado:
            return None
        coincidencia = next(
            (s for s in segmentos_resultado["segmentos"] if s["nombre"] == tesis["metrica_campo"]),
            None,
        )
        if coincidencia is None:
            return None
        return {
            "periodo": periodo,
            "fecha_reporte": ahora.date().isoformat(),
            "valor": coincidencia["var_pct"],
            "semaforo": calcular_semaforo(
                coincidencia["var_pct"], tesis["umbral_verde"], tesis["umbral_rojo"], tesis["direccion"]
            ),
            "fuente_url": segmentos_resultado["fuente_url"],
            "cita_textual": coincidencia["cita"],
            "extraido_por": "segmento",
        }

    return None
