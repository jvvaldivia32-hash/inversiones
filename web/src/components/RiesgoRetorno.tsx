import type { RiesgoRetorno as TipoRiesgoRetorno } from "../types";
import { formatNumeroCL, formatPct } from "../lib/format";
import "./RiesgoRetorno.css";

const HORIZONTES = ["1A", "3A", "5A", "10A"] as const;

// Sin color a propósito (regla dura: el color es solo señal). Un retorno negativo o una
// volatilidad alta no son un "estado" de la empresa, son su historia de precio.
export default function RiesgoRetorno({ datos }: { datos: TipoRiesgoRetorno }) {
  const retornos = HORIZONTES.filter((h) => datos.retorno_anual_pct?.[h] !== undefined);

  return (
    <section className="riesgo-retorno" aria-label="Riesgo y retorno">
      <dl>
        {retornos.map((h) => (
          <div key={h}>
            <dt>Retorno anual {h}</dt>
            <dd>{formatPct(datos.retorno_anual_pct![h]!)}</dd>
          </div>
        ))}
        {datos.volatilidad_anual_pct !== undefined && (
          <div>
            <dt>Volatilidad anual</dt>
            <dd>{formatNumeroCL(datos.volatilidad_anual_pct, 1)}%</dd>
          </div>
        )}
        {datos.caida_maxima_5a_pct !== undefined && (
          <div>
            <dt>Caída máxima 5A</dt>
            <dd>{formatPct(datos.caida_maxima_5a_pct)}</dd>
          </div>
        )}
      </dl>
      <p className="riesgo-retorno-nota">Solo precio, sin dividendos · definiciones en el Diccionario</p>
    </section>
  );
}
