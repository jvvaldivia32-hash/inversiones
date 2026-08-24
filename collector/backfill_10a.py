"""Backfill de una sola vez: extiende historico_precios.json de 5 a 10 años.

Por qué hace falta un script aparte y no alcanza con subir DIAS_MAX: `compactar()` **borra**
en cada corrida horaria todo lo más viejo que el corte. Cuando el corte eran 5 años, cada
corrida fue tirando a la basura lo anterior — así que el histórico viejo de los tickers
actuales ya no está en el archivo y no hay forma de recuperarlo desde adentro. Hay que
volver a pedírselo a Yahoo.

Es idempotente y no destructivo: mezcla lo que Yahoo devuelve con lo que ya hay, y ante un
choque en el mismo timestamp **gana lo que ya estaba guardado**. Eso importa porque los
últimos 45 días tienen resolución horaria propia (recolectada hora a hora por el cron) que
Yahoo no puede devolver — el backfill solo rellena hacia atrás, nunca pisa lo fino.

Se corre a mano una vez:

    python collector/backfill_10a.py            # todos los tickers del archivo
    python collector/backfill_10a.py MSFT AAPL  # solo esos

No está en ningún workflow a propósito: pegarle a Yahoo por 83 tickers es justo el tipo de
cosa que conviene hacer una vez y mirar el resultado, no dejar corriendo por cron.
"""

import datetime
import sys
import time
from pathlib import Path

import historico
from sources import yahoo

RAIZ_REPO = Path(__file__).resolve().parent.parent
RUTA_HISTORICO = RAIZ_REPO / "data" / "historico_precios.json"

PAUSA_ENTRE_TICKERS_S = 1.0  # cortesía con Yahoo; son ~83 tickers, no hay apuro


def mezclar(serie_existente: list[dict], puntos_yahoo: list[dict]) -> list[dict]:
    """Une el backfill con lo ya guardado. Clave de deduplicación: el timestamp exacto.
    Lo ya guardado gana siempre — ver el docstring del módulo."""
    por_ts = {f"{p['fecha']}T00:00:00": {"ts": f"{p['fecha']}T00:00:00", "valor": p["valor"]} for p in puntos_yahoo}
    for punto in serie_existente:
        por_ts[punto["ts"]] = punto
    return sorted(por_ts.values(), key=lambda p: p["ts"])


def main() -> None:
    ahora = datetime.datetime.now(datetime.timezone.utc)
    hist = historico.cargar(RUTA_HISTORICO)
    if not hist:
        print(f"No hay nada en {RUTA_HISTORICO} — nada que extender.")
        return

    tickers = sys.argv[1:] or sorted(hist)
    print(f"Extendiendo a {historico.DIAS_MAX // 365} años: {len(tickers)} ticker(s).\n")

    sin_respuesta = []
    for i, ticker in enumerate(tickers, 1):
        antes = len(hist.get(ticker, []))
        primero_antes = hist.get(ticker, [{}])[0].get("ts", "—")[:10] if antes else "—"

        puntos = yahoo.descargar_historico(ticker, dias=historico.DIAS_MAX)
        if not puntos:
            # Degradación silenciosa igual que el resto de sources/: si Yahoo no responde
            # por un ticker, ese ticker se queda con la historia que ya tenía. No se aborta
            # el backfill entero por uno.
            sin_respuesta.append(ticker)
            print(f"[{i}/{len(tickers)}] {ticker}: Yahoo no devolvió nada, se deja como estaba")
            continue

        hist[ticker] = mezclar(hist.get(ticker, []), puntos)
        print(
            f"[{i}/{len(tickers)}] {ticker}: {antes} -> {len(hist[ticker])} puntos "
            f"(desde {primero_antes} -> {hist[ticker][0]['ts'][:10]})"
        )
        time.sleep(PAUSA_ENTRE_TICKERS_S)

    print("\nCompactando con la escalera nueva (horario 45d / diario 2a / semanal 10a)...")
    antes_total = sum(len(s) for s in hist.values())
    historico.compactar(hist, ahora)
    despues_total = sum(len(s) for s in hist.values())
    print(f"Puntos totales: {antes_total} -> {despues_total}")

    historico.guardar(RUTA_HISTORICO, hist)
    print(f"Guardado en {RUTA_HISTORICO} ({RUTA_HISTORICO.stat().st_size / 1_000_000:.1f} MB).")
    if sin_respuesta:
        print(f"\nSin respuesta de Yahoo ({len(sin_respuesta)}): {', '.join(sin_respuesta)}")
        print("Volver a correr el script solo con esos tickers para reintentar.")


if __name__ == "__main__":
    main()
