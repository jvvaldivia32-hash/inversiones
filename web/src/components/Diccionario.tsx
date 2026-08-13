import rawDaily from "../data/daily.json";
import type { DailyData } from "../types";
import { DICCIONARIO, type CampoFundamentalEjemplo } from "../data/diccionario";
import { formatNumeroCL } from "../lib/format";
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
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
