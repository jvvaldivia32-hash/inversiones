import type { MetricasAvanzadas as TipoMetricasAvanzadas } from "../types";
import { formatMusd, formatNumeroCL, formatUSD } from "../lib/format";
import {
  contextoRoe,
  contextoRoicRoce,
  contextoMargenOperativo,
  contextoDeudaNetaEbitda,
  contextoDeudaPatrimonio,
  contextoPE,
  contextoDividendYield,
  contextoPayoutRatio,
  contextoBeta,
} from "../lib/referenciasMetricas";
import "./MetricasAvanzadas.css";

type Metrica = {
  etiqueta: string;
  valor: number | null;
  formatear: (v: number) => string;
  contexto?: (v: number) => string;
};

const formatX = (v: number) => `${formatNumeroCL(v, 2)}x`;
const formatPctPlano = (v: number) => `${formatNumeroCL(v, 1)}%`;

function categorias(m: TipoMetricasAvanzadas): { titulo: string; metricas: Metrica[] }[] {
  return [
    {
      titulo: "Estructura de capital",
      metricas: [
        { etiqueta: "Market cap", valor: m.market_cap_musd, formatear: formatMusd },
        { etiqueta: "Enterprise value", valor: m.enterprise_value_musd, formatear: formatMusd },
        { etiqueta: "Deuda neta", valor: m.deuda_neta_musd, formatear: formatMusd },
        {
          etiqueta: "Deuda neta / EBITDA",
          valor: m.deuda_neta_ebitda,
          formatear: formatX,
          contexto: contextoDeudaNetaEbitda,
        },
        {
          etiqueta: "Deuda / patrimonio",
          valor: m.deuda_patrimonio,
          formatear: formatX,
          contexto: contextoDeudaPatrimonio,
        },
      ],
    },
    {
      titulo: "Rentabilidad",
      metricas: [
        { etiqueta: "Margen bruto", valor: m.margen_bruto_pct, formatear: formatPctPlano },
        {
          etiqueta: "Margen EBIT",
          valor: m.margen_ebit_pct,
          formatear: formatPctPlano,
          contexto: contextoMargenOperativo,
        },
        { etiqueta: "ROA", valor: m.roa_pct, formatear: formatPctPlano },
        { etiqueta: "ROE", valor: m.roe_pct, formatear: formatPctPlano, contexto: contextoRoe },
        {
          etiqueta: "ROIC (aprox.)",
          valor: m.roic_pct,
          formatear: formatPctPlano,
          contexto: contextoRoicRoce,
        },
        { etiqueta: "ROCE", valor: m.roce_pct, formatear: formatPctPlano, contexto: contextoRoicRoce },
      ],
    },
    {
      titulo: "Valoración",
      metricas: [
        { etiqueta: "P/E", valor: m.pe, formatear: formatX, contexto: contextoPE },
        { etiqueta: "EV / Ingresos", valor: m.ev_ingresos, formatear: formatX },
        { etiqueta: "EV / EBITDA", valor: m.ev_ebitda, formatear: formatX },
        { etiqueta: "P / Valor libro", valor: m.p_vl, formatear: formatX },
        {
          etiqueta: "Dividend yield",
          valor: m.dividend_yield_pct,
          formatear: formatPctPlano,
          contexto: contextoDividendYield,
        },
        {
          etiqueta: "Payout ratio",
          valor: m.payout_ratio_pct,
          formatear: formatPctPlano,
          contexto: contextoPayoutRatio,
        },
      ],
    },
    {
      titulo: "Riesgo",
      metricas: [
        { etiqueta: "Máximo 52 semanas", valor: m.maximo_52s, formatear: formatUSD },
        { etiqueta: "Mínimo 52 semanas", valor: m.minimo_52s, formatear: formatUSD },
        {
          etiqueta: "Beta (propio, vs. VOO)",
          valor: m.beta,
          formatear: (v) => formatNumeroCL(v, 2),
          contexto: contextoBeta,
        },
      ],
    },
  ];
}

export default function MetricasAvanzadas({ metricas }: { metricas: TipoMetricasAvanzadas }) {
  const bloques = categorias(metricas)
    .map((c) => ({ ...c, metricas: c.metricas.filter((m) => m.valor !== null) }))
    .filter((c) => c.metricas.length > 0);

  if (bloques.length === 0) {
    return <p className="metricas-avanzadas-vacio">Sin datos suficientes todavía para calcular esto.</p>;
  }

  return (
    <div className="metricas-avanzadas-grid">
      {bloques.map((bloque) => (
        <div key={bloque.titulo} className="metricas-avanzadas-categoria">
          <h5>{bloque.titulo}</h5>
          <dl>
            {bloque.metricas.map((m) => (
              <div key={m.etiqueta} className="metricas-avanzadas-fila">
                <dt>{m.etiqueta}</dt>
                <dd>{m.formatear(m.valor as number)}</dd>
                {m.contexto && (
                  <p className="metricas-avanzadas-contexto">{m.contexto(m.valor as number)}</p>
                )}
              </div>
            ))}
          </dl>
        </div>
      ))}
    </div>
  );
}
