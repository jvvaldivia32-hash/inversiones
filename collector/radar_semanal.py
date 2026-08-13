"""Orquestador del Radar (Fase 6) — corre semanal, no cada hora como main.py: los
fundamentales de ~80 tickers no cambian de un día para otro, y no tiene sentido pegarle a
EDGAR con esa frecuencia para nada. Ver .github/workflows/radar_semanal.yml.
"""

import datetime
import json
from pathlib import Path

import historico
import radar
from env import cargar_env
from sources import edgar, prices, yahoo
from universo_radar import UNIVERSO

RAIZ_REPO = Path(__file__).resolve().parent.parent
RUTA_HISTORICO = RAIZ_REPO / "data" / "historico_precios.json"
RUTA_DAILY = RAIZ_REPO / "data" / "daily.json"


def actualizar_precios_universo(hist: dict, ahora: datetime.datetime) -> None:
    for ticker in UNIVERSO:
        if ticker not in hist:
            backfill = yahoo.descargar_historico(ticker)
            if backfill:
                historico.sembrar(hist, ticker, backfill)
        try:
            cot = prices.obtener_cotizacion(ticker)
            historico.agregar_punto(hist, ticker, ahora, cot["precio"])
        except prices.FinnhubError as e:
            print(f"  {ticker}: no se pudo actualizar el precio ({e})")


def _formatear_motivo_candidato(ingresos_var_pct: float, margen_op: float, flujo_op_positivo: bool, deuda_patrimonio: float | None) -> str:
    partes = [f"Ingresos {ingresos_var_pct:+.0f}% YoY", f"margen operativo {margen_op:.0f}%"]
    partes.append("flujo operativo positivo" if flujo_op_positivo else "flujo operativo negativo")
    if deuda_patrimonio is not None:
        partes.append(f"deuda/patrimonio {deuda_patrimonio:.1f}")
    return ", ".join(partes)


def evaluar_universo(hist: dict, ahora: datetime.datetime) -> dict:
    """{"candidatos": [...], "descartados": [...], "ultima_corrida": ...} — shape de
    RadarData en web/src/types.ts. Empresas no castigadas no aparecen en ningún lado (no
    son el punto del radar); castigadas sin suficiente dato para evaluar "sana" tampoco
    aparecen — mejor ausente que con un veredicto inventado."""
    castigadas = {}
    for ticker in UNIVERSO:
        resultado = radar.computar_castigada(hist.get(ticker, []), ahora)
        if resultado and resultado["castigada"]:
            castigadas[ticker] = resultado

    print(f"Castigadas: {len(castigadas)}/{len(UNIVERSO)}")

    ciks = edgar.resolver_ciks(list(castigadas))

    candidatos = []
    descartados = []
    for ticker, precio_info in castigadas.items():
        cik = ciks.get(ticker)
        if cik is None:
            continue
        try:
            fund = edgar.obtener_fundamentales(ticker, cik, None)
        except edgar.EdgarError:
            continue
        if fund is None:
            continue

        es_banco = ticker in radar.BANCOS
        deuda_patrimonio = None
        if not es_banco:
            try:
                deuda_patrimonio = edgar.obtener_deuda_patrimonio(cik)
            except edgar.EdgarError:
                pass

        veredicto = radar.evaluar_sana(fund["series"], deuda_patrimonio, es_banco)
        if veredicto is None:
            continue

        ingresos = fund["series"]["ingresos_musd"]
        margen = fund["series"]["margen_operativo"]
        flujo_op = fund["series"]["flujo_op_musd"]
        ingresos_var_pct = (ingresos[-1]["valor"] / ingresos[-5]["valor"] - 1) * 100

        if veredicto["sana"]:
            candidatos.append(
                {
                    "ticker": ticker,
                    "nombre": UNIVERSO[ticker],
                    "pct_bajo_maximo": precio_info["pct_bajo_maximo"],
                    "motivo": _formatear_motivo_candidato(
                        ingresos_var_pct, margen[-1]["valor"], flujo_op[-1]["valor"] > 0, deuda_patrimonio
                    ),
                    "metricas": {
                        "ingresos_var_pct": round(ingresos_var_pct, 1),
                        "margen_op": round(margen[-1]["valor"], 1),
                        "deuda_patrimonio": round(deuda_patrimonio, 2) if deuda_patrimonio is not None else None,
                    },
                    "serie_precio": historico.derivar_rangos(hist.get(ticker, []), ahora),
                }
            )
        else:
            descartados.append(
                {
                    "ticker": ticker,
                    "pct_bajo_maximo": precio_info["pct_bajo_maximo"],
                    "motivo_descarte": "; ".join(veredicto["motivos"]),
                }
            )

    return {
        "candidatos": candidatos,
        "descartados": descartados,
        "ultima_corrida": ahora.date().isoformat(),
    }


def main() -> None:
    cargar_env(RAIZ_REPO / ".env")
    ahora = datetime.datetime.now(datetime.timezone.utc)

    hist = historico.cargar(RUTA_HISTORICO)
    print("Actualizando precios del universo del radar...")
    actualizar_precios_universo(hist, ahora)
    historico.compactar(hist, ahora)
    historico.guardar(RUTA_HISTORICO, hist)

    print("Evaluando castigada + sana...")
    radar_data = evaluar_universo(hist, ahora)
    print(f"Candidatos: {len(radar_data['candidatos'])}, descartados: {len(radar_data['descartados'])}")

    daily = json.loads(RUTA_DAILY.read_text(encoding="utf-8"))
    daily["radar"] = radar_data
    RUTA_DAILY.write_text(json.dumps(daily, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("data/daily.json actualizado.")


if __name__ == "__main__":
    main()
