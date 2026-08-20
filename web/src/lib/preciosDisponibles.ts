import type { DailyData, SeriePrecio } from "../types";

// Universo comprable del simulador de "paper investing" (extra 2026-08-20): watchlist +
// candidatos del Radar — los únicos que ya traen precio y serie_precio completos en
// daily.json hoy (los descartados del Radar no tienen serie_precio, no hay nada que
// graficar). No pide nada nuevo al collector, solo combina lo que ya existe.
export interface PrecioDisponible {
  ticker: string;
  nombre: string;
  precio: number;
  serie_precio: SeriePrecio;
}

export function preciosDisponibles(daily: DailyData): Record<string, PrecioDisponible> {
  const resultado: Record<string, PrecioDisponible> = {};

  for (const p of daily.posiciones) {
    resultado[p.ticker] = {
      ticker: p.ticker,
      nombre: p.nombre,
      precio: p.precio,
      serie_precio: p.serie_precio,
    };
  }

  for (const c of daily.radar.candidatos) {
    if (resultado[c.ticker]) continue; // ya está en la watchlist, no lo pisa
    resultado[c.ticker] = {
      ticker: c.ticker,
      nombre: c.nombre,
      precio: c.serie_precio["1M"].at(-1)?.valor ?? c.serie_precio["1A"].at(-1)?.valor ?? 0,
      serie_precio: c.serie_precio,
    };
  }

  return resultado;
}
