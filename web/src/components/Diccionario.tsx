import rawDaily from "../data/daily.json";
import type { DailyData } from "../types";
import { DICCIONARIO, type CampoFundamentalEjemplo, type CampoMetricaAvanzadaEjemplo } from "../data/diccionario";
import { formatMusd, formatNumeroCL } from "../lib/format";
import Cifra from "./Cifra";
import "./Diccionario.css";

const daily = rawDaily as unknown as DailyData;

const FORMATEAR: Record<CampoFundamentalEjemplo, (v: number) => string> = {
  ingresos_musd: (v) => `US$${formatNumeroCL(v, 0)}M`,
  op_income_musd: (v) => `US$${formatNumeroCL(v, 0)}M`,
  eps_gaap: (v) => `US$${formatNumeroCL(v, 2)}`,
  margen_operativo: (v) => `${formatNumeroCL(v, 1)}%`,
  capex_musd: (v) => `US$${formatNumeroCL(v, 0)}M`,
  flujo_op_musd: (v) => `US$${formatNumeroCL(v, 0)}M`,
};

const formatX = (v: number) => `${formatNumeroCL(v, 2)}x`;
const formatPctPlano = (v: number) => `${formatNumeroCL(v, 1)}%`;

const FORMATEAR_AVANZADA: Record<CampoMetricaAvanzadaEjemplo, (v: number) => string> = {
  market_cap_musd: formatMusd,
  enterprise_value_musd: formatMusd,
  deuda_neta_musd: formatMusd,
  deuda_neta_ebitda: formatX,
  margen_bruto_pct: formatPctPlano,
  margen_ebit_pct: formatPctPlano,
  roa_pct: formatPctPlano,
  roe_pct: formatPctPlano,
  roic_pct: formatPctPlano,
  roce_pct: formatPctPlano,
  pe: formatX,
  ev_ingresos: formatX,
  ev_ebitda: formatX,
  p_vl: formatX,
  dividend_yield_pct: formatPctPlano,
  payout_ratio_pct: formatPctPlano,
  beta: (v) => formatNumeroCL(v, 2),
};

function buscarEjemploFundamental(campo: CampoFundamentalEjemplo) {
  for (const p of daily.posiciones) {
    const serie = p.fundamentales?.series[campo];
    if (serie && serie.length > 0) {
      const ultimo = serie[serie.length - 1];
      return { ticker: p.ticker, periodo: ultimo.periodo, valor: ultimo.valor, fuenteUrl: p.fundamentales!.fuente_url };
    }
  }
  return null;
}

function buscarEjemploMetricaAvanzada(campo: CampoMetricaAvanzadaEjemplo) {
  for (const p of daily.posiciones) {
    const valor = p.metricas_avanzadas?.[campo];
    if (valor !== null && valor !== undefined) {
      return { ticker: p.ticker, valor };
    }
  }
  return null;
}

function buscarEjemploDeudaPatrimonio() {
  const candidato = daily.radar?.candidatos?.find((c) => c.metricas.deuda_patrimonio !== null);
  if (!candidato) return null;
  return { ticker: candidato.ticker, valor: candidato.metricas.deuda_patrimonio! };
}

export default function Diccionario() {
  return (
    <dl className="diccionario">
      {DICCIONARIO.map((entrada) => {
        const ejemploFundamental = entrada.campoEjemplo ? buscarEjemploFundamental(entrada.campoEjemplo) : null;
        const ejemploDeuda = entrada.esDeudaPatrimonio ? buscarEjemploDeudaPatrimonio() : null;
        const ejemploAvanzada = entrada.campoMetricaAvanzada
          ? buscarEjemploMetricaAvanzada(entrada.campoMetricaAvanzada)
          : null;

        return (
          <div key={entrada.id} className="diccionario-entrada">
            <dt>{entrada.termino}</dt>
            <dd>
              <p>{entrada.definicion}</p>
              {ejemploFundamental && entrada.campoEjemplo && (
                <p className="diccionario-ejemplo">
                  Ejemplo real ({ejemploFundamental.ticker}, {ejemploFundamental.periodo}):{" "}
                  <Cifra
                    valor={FORMATEAR[entrada.campoEjemplo](ejemploFundamental.valor)}
                    fuente="SEC EDGAR"
                    url={ejemploFundamental.fuenteUrl}
                  />
                </p>
              )}
              {ejemploDeuda && (
                <p className="diccionario-ejemplo">
                  Ejemplo real ({ejemploDeuda.ticker}, del Radar): deuda/patrimonio ={" "}
                  {formatNumeroCL(ejemploDeuda.valor, 2)}
                </p>
              )}
              {ejemploAvanzada && entrada.campoMetricaAvanzada && (
                <p className="diccionario-ejemplo">
                  Ejemplo real ({ejemploAvanzada.ticker}): {FORMATEAR_AVANZADA[entrada.campoMetricaAvanzada](ejemploAvanzada.valor)}
                </p>
              )}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
