import type { CapmData, SeriePrecio } from "../types";

// Análisis de una cartera (simulada o real) a partir de lo que publica el recolector
// (collector/capm.py). Se arma en el navegador y no en el recolector porque "Mi inversión"
// vive en el repo privado, que el recolector no puede leer (excepción #3 de CLAUDE.md).
//
// Todo con los pesos de HOY: "si hubieras tenido esta misma cartera todo el último año".

export interface Peso {
  ticker: string;
  valor: number;
  peso: number; // 0..1 sobre lo invertido
  sector: string;
}

export interface Analisis {
  total: number;
  pesos: Peso[];
  sectores: { sector: string; peso: number }[];
  // Solo con los tickers que tienen un año de historia (los demás van en `sinHistoria`).
  beta?: number;
  volatilidad?: number;
  volatilidadSinDiversificar?: number;
  correlacionPromedio?: number;
  retorno1a?: number;
  esperadoCapm?: number;
  diferencia?: number;
  mercado1a?: number;
  sinHistoria: string[];
}

const SIN_SECTOR = "Fondo indexado / sin dato";

export function analizarCartera(
  valores: Record<string, number>,
  capm: CapmData | undefined,
  sectores: Record<string, string | null> | undefined,
): Analisis | null {
  const entradas = Object.entries(valores).filter(([, v]) => v > 0);
  const total = entradas.reduce((acc, [, v]) => acc + v, 0);
  if (total <= 0) return null;

  const pesos = entradas
    .map(([ticker, valor]) => ({
      ticker,
      valor,
      peso: valor / total,
      sector: sectores?.[ticker] ?? SIN_SECTOR,
    }))
    .sort((a, b) => b.peso - a.peso);

  const porSector = new Map<string, number>();
  for (const p of pesos) porSector.set(p.sector, (porSector.get(p.sector) ?? 0) + p.peso);
  const sectoresOrdenados = [...porSector.entries()]
    .map(([sector, peso]) => ({ sector, peso }))
    .sort((a, b) => b.peso - a.peso);

  const conDatos = pesos.filter((p) => capm?.por_ticker[p.ticker]);
  const sinHistoria = pesos.filter((p) => !capm?.por_ticker[p.ticker]).map((p) => p.ticker);
  const base: Analisis = { total, pesos, sectores: sectoresOrdenados, sinHistoria };
  if (!capm || conDatos.length === 0) return base;

  // Se re-normaliza sobre lo que tiene datos, para que beta/σ/CAPM sean de una cartera real.
  const totalConDatos = conDatos.reduce((acc, p) => acc + p.valor, 0);
  const w = conDatos.map((p) => p.valor / totalConDatos);
  const datos = conDatos.map((p) => capm.por_ticker[p.ticker]);

  const suma = (f: (i: number) => number) => w.reduce((acc, _, i) => acc + f(i), 0);
  const beta = suma((i) => w[i] * datos[i].beta);
  const retorno1a = suma((i) => w[i] * datos[i].retorno_1a_pct);
  const esperadoCapm = suma((i) => w[i] * datos[i].esperado_capm_pct);
  const mercado1a = suma((i) => w[i] * datos[i].mercado_1a_pct);
  const volatilidadSinDiversificar = suma((i) => w[i] * datos[i].volatilidad_pct);

  // σ²_cartera = Σ_i Σ_j w_i w_j σ_i σ_j ρ_ij
  const idx = new Map(capm.correlaciones.tickers.map((t, i) => [t, i]));
  let varianza = 0;
  let faltaCorrelacion = false;
  let sumaCorr = 0;
  let pares = 0;
  conDatos.forEach((a, i) => {
    conDatos.forEach((b, j) => {
      const rho = capm.correlaciones.matriz[idx.get(a.ticker) ?? -1]?.[idx.get(b.ticker) ?? -1];
      if (rho === null || rho === undefined) {
        faltaCorrelacion = true;
        return;
      }
      varianza += w[i] * w[j] * datos[i].volatilidad_pct * datos[j].volatilidad_pct * rho;
      if (j > i) {
        sumaCorr += rho;
        pares += 1;
      }
    });
  });

  return {
    ...base,
    beta,
    retorno1a,
    esperadoCapm,
    diferencia: retorno1a - esperadoCapm,
    mercado1a,
    volatilidadSinDiversificar,
    volatilidad: faltaCorrelacion ? undefined : Math.sqrt(varianza),
    correlacionPromedio: pares > 0 && !faltaCorrelacion ? sumaCorr / pares : undefined,
  };
}

// Precio de cierre en o antes de `fecha` (YYYY-MM-DD) dentro de la serie de 1 año (un
// punto por día). null si la fecha es anterior a la serie.
export function precioEnFecha(serie: SeriePrecio, fecha: string): number | null {
  const previos = serie["1A"].filter((p) => p.fecha.slice(0, 10) <= fecha);
  return previos.length > 0 ? previos[previos.length - 1].valor : null;
}

// "¿Y si cada peso que entró al simulador hubiera ido al S&P 500 (VOO) el mismo día?"
export function valorSiFueraAlSP500(
  flujos: { fecha: string; monto_usd: number }[],
  serieVoo: SeriePrecio,
  precioVooHoy: number,
): number | null {
  let unidades = 0;
  for (const f of flujos) {
    const precio = precioEnFecha(serieVoo, f.fecha);
    if (!precio) return null;
    unidades += f.monto_usd / precio;
  }
  return unidades * precioVooHoy;
}
