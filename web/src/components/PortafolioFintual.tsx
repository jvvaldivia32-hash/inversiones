import type { Fintual } from "../types";
import { formatFechaCorta, formatNumeroCL } from "../lib/format";
import "./PortafolioFintual.css";

// La API de Fintual no dice en qué moneda viene `nav` — se asume CLP (fondos mutuos
// chilenos, mismo formato que UF/Dólar en Referencias.tsx) hasta confirmar lo contrario.
function formatCLP(valor: number): string {
  return `$${formatNumeroCL(valor, 0)}`;
}

export default function PortafolioFintual({ fintual }: { fintual: Fintual }) {
  return (
    <div className="portafolio-fintual">
      <p className="portafolio-fintual-total">
        Saldo total <strong>{formatCLP(fintual.saldo_total)}</strong>
      </p>
      <ul className="portafolio-fintual-goals">
        {fintual.goals.map((g) => (
          <li key={g.id}>
            <span className="portafolio-fintual-nombre">{g.nombre}</span>
            <span className="portafolio-fintual-saldo">{formatCLP(g.saldo)}</span>
          </li>
        ))}
      </ul>
      <p className="portafolio-fintual-nota">
        Solo saldo actual — Fintual no expone rentabilidad ni histórico de aportes por
        API. Actualizado {formatFechaCorta(fintual.actualizado)}.
      </p>
    </div>
  );
}
