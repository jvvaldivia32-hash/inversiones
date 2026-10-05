import type { CapmData } from "../types";
import { analizarCartera } from "../lib/cartera";
import { formatNumeroCL, formatPct, formatUSD } from "../lib/format";
import "./AnalisisCartera.css";

export interface ComparacionSP500 {
  desde: string;
  aportado: number;
  valorCartera: number;
  valorSP500: number;
}

interface Props {
  valores: Record<string, number>; // USD de hoy por ticker
  capm: CapmData | undefined;
  sectores: Record<string, string | null> | undefined;
  comparacion?: ComparacionSP500 | null;
  efectivo?: number;
}

function Pct({ valor }: { valor: number }) {
  return <>{formatNumeroCL(valor * 100, 1)}%</>;
}

// Sin color salvo la diferencia contra el CAPM y contra el S&P 500 (las dos son
// "rindió más / rindió menos", mismo criterio que la variación diaria). Las barras de
// concentración van en gris: el peso de una acción no es un estado bueno ni malo.
export default function AnalisisCartera({ valores, capm, sectores, comparacion, efectivo }: Props) {
  const a = analizarCartera(valores, capm, sectores);
  if (!a) return null;

  const retCartera = comparacion ? (comparacion.valorCartera / comparacion.aportado - 1) * 100 : null;
  const retSP = comparacion ? (comparacion.valorSP500 / comparacion.aportado - 1) * 100 : null;

  return (
    <section className="analisis-cartera" aria-label="Análisis de la cartera">
      {comparacion && retCartera !== null && retSP !== null && (
        <div className="analisis-bloque">
          <h4>Contra el S&P 500</h4>
          <dl>
            <div>
              <dt>Tu cartera desde {comparacion.desde}</dt>
              <dd>{formatPct(retCartera)}</dd>
            </div>
            <div>
              <dt>Misma plata, mismos días, en VOO</dt>
              <dd>{formatPct(retSP)}</dd>
            </div>
            <div>
              <dt>Diferencia</dt>
              <dd className={retCartera - retSP >= 0 ? "var-positiva" : "var-negativa"}>
                {retCartera - retSP > 0 ? "+" : ""}
                {formatNumeroCL(retCartera - retSP, 1)} pts
              </dd>
            </div>
          </dl>
          <p className="analisis-nota">
            Incluye el efectivo sin invertir: plata parada también cuenta contra el índice.
          </p>
        </div>
      )}

      {a.retorno1a !== undefined && a.esperadoCapm !== undefined && a.diferencia !== undefined && (
        <div className="analisis-bloque">
          <h4>CAPM de la cartera · último año</h4>
          <dl>
            <div>
              <dt>Rindió</dt>
              <dd>{formatPct(a.retorno1a)}</dd>
            </div>
            <div>
              <dt>S&P 500</dt>
              <dd>{a.mercado1a !== undefined ? formatPct(a.mercado1a) : "—"}</dd>
            </div>
            <div>
              <dt>CAPM esperaba</dt>
              <dd>{formatPct(a.esperadoCapm)}</dd>
            </div>
            <div>
              <dt>Diferencia</dt>
              <dd className={a.diferencia >= 0 ? "var-positiva" : "var-negativa"}>
                {a.diferencia > 0 ? "+" : ""}
                {formatNumeroCL(a.diferencia, 1)} pts
              </dd>
            </div>
          </dl>
          <p className="analisis-nota">
            Con los pesos de hoy, como si hubieras tenido esta misma cartera todo el último año.
            Solo precio, sin dividendos.
          </p>
        </div>
      )}

      {a.beta !== undefined && (
        <div className="analisis-bloque">
          <h4>Riesgo</h4>
          <dl>
            <div>
              <dt>β de la cartera</dt>
              <dd>{formatNumeroCL(a.beta, 2)}</dd>
            </div>
            {a.volatilidad !== undefined && (
              <div>
                <dt>Volatilidad anual</dt>
                <dd>{formatNumeroCL(a.volatilidad, 1)}%</dd>
              </div>
            )}
            {a.volatilidadSinDiversificar !== undefined && (
              <div>
                <dt>Sin diversificar sería</dt>
                <dd>{formatNumeroCL(a.volatilidadSinDiversificar, 1)}%</dd>
              </div>
            )}
            {a.correlacionPromedio !== undefined && (
              <div>
                <dt>Correlación promedio</dt>
                <dd>{formatNumeroCL(a.correlacionPromedio, 2)}</dd>
              </div>
            )}
          </dl>
          <p className="analisis-nota">
            "Sin diversificar" es el promedio ponderado de la volatilidad de cada acción: lo que
            tendrías si todas se movieran siempre juntas. La distancia hasta la volatilidad real
            es lo que te ahorra la diversificación.
          </p>
        </div>
      )}

      <div className="analisis-bloque">
        <h4>Concentración</h4>
        <div className="analisis-concentracion">
          <ul>
            {a.pesos.map((p) => (
              <li key={p.ticker}>
                <span>{p.ticker}</span>
                <span className="analisis-barra" aria-hidden="true">
                  <span style={{ width: `${p.peso * 100}%` }} />
                </span>
                <span className="analisis-num">
                  <Pct valor={p.peso} />
                </span>
              </li>
            ))}
          </ul>
          <ul>
            {a.sectores.map((s) => (
              <li key={s.sector}>
                <span>{s.sector}</span>
                <span className="analisis-barra" aria-hidden="true">
                  <span style={{ width: `${s.peso * 100}%` }} />
                </span>
                <span className="analisis-num">
                  <Pct valor={s.peso} />
                </span>
              </li>
            ))}
          </ul>
        </div>
        <p className="analisis-nota">
          Sobre {formatUSD(a.total)} invertidos
          {efectivo !== undefined && efectivo > 0 ? ` (sin contar ${formatUSD(efectivo)} en efectivo)` : ""}.
          {a.sinHistoria.length > 0 &&
            ` Sin un año de historia, fuera del riesgo y el CAPM: ${a.sinHistoria.join(", ")}.`}
        </p>
      </div>
    </section>
  );
}
