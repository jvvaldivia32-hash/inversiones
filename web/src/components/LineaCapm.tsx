import type { CapmData } from "../types";
import { formatNumeroCL, formatPct } from "../lib/format";
import "./RiesgoRetorno.css";

function fechaLarga(iso: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric" }).format(
    new Date(`${iso}T12:00:00`),
  );
}

// Rindió vs. lo que el CAPM esperaba dada su beta, en el último año. La diferencia lleva
// verde/rojo (decisión de José, 2026-10-05) como cualquier variación: es un dato del
// pasado, no un veredicto — acá nunca se dice "compra" ni "barata" (regla dura del Radar).
export default function LineaCapm({ ticker, capm }: { ticker: string; capm: CapmData }) {
  const d = capm.por_ticker[ticker];
  if (!d) return null;

  return (
    <section className="riesgo-retorno" aria-label="CAPM del último año">
      <dl>
        <div>
          <dt>Rindió (1 año)</dt>
          <dd>{formatPct(d.retorno_1a_pct)}</dd>
        </div>
        <div>
          <dt>CAPM esperaba</dt>
          <dd>{formatPct(d.esperado_capm_pct)}</dd>
        </div>
        <div>
          <dt>Diferencia</dt>
          <dd className={d.diferencia_pts >= 0 ? "var-positiva" : "var-negativa"}>
            {d.diferencia_pts > 0 ? "+" : ""}
            {formatNumeroCL(d.diferencia_pts, 1)} pts
          </dd>
        </div>
        <div>
          <dt>β 1 año</dt>
          <dd>{formatNumeroCL(d.beta, 2)}</dd>
        </div>
      </dl>
      <p className="riesgo-retorno-nota">
        CAPM: {formatNumeroCL(capm.rf_pct, 2)}% (bono EE.UU. 1 año, {fechaLarga(capm.rf_fecha)}) + β ×
        (S&P 500 {formatPct(d.mercado_1a_pct)} − {formatNumeroCL(capm.rf_pct, 2)}%) · del {fechaLarga(d.desde)} al{" "}
        {fechaLarga(d.hasta)} · solo precio, sin dividendos
      </p>
    </section>
  );
}
