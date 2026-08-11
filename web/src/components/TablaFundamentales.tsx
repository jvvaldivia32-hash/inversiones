import type { Fundamentales, PuntoFundamental } from "../types";
import { formatNumeroCL } from "../lib/format";
import "./TablaFundamentales.css";

interface Fila {
  etiqueta: string;
  datos: PuntoFundamental[];
  formatear: (valor: number) => string;
}

export default function TablaFundamentales({
  fundamentales,
}: {
  fundamentales: Fundamentales;
}) {
  const s = fundamentales.series;
  const periodos = s.ingresos_musd.map((p) => p.periodo);

  const filas: Fila[] = [
    { etiqueta: "Ingresos", datos: s.ingresos_musd, formatear: (v) => `$${formatNumeroCL(v, 0)}M` },
    { etiqueta: "Operating income", datos: s.op_income_musd, formatear: (v) => `$${formatNumeroCL(v, 0)}M` },
    { etiqueta: "EPS diluido (GAAP)", datos: s.eps_gaap, formatear: (v) => `$${formatNumeroCL(v, 2)}` },
    { etiqueta: "EPS (non-GAAP)", datos: s.eps_non_gaap, formatear: (v) => `$${formatNumeroCL(v, 2)}` },
    { etiqueta: "Margen operativo", datos: s.margen_operativo, formatear: (v) => `${formatNumeroCL(v, 1)}%` },
    { etiqueta: "Capex", datos: s.capex_musd, formatear: (v) => `$${formatNumeroCL(v, 0)}M` },
    { etiqueta: "Flujo operativo", datos: s.flujo_op_musd, formatear: (v) => `$${formatNumeroCL(v, 0)}M` },
  ];

  return (
    <div className="tabla-fundamentales-wrap">
      <table className="tabla-fundamentales">
        <thead>
          <tr>
            <th></th>
            {periodos.map((p) => (
              <th key={p}>{p}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.map((fila) => (
            <tr key={fila.etiqueta}>
              <th scope="row">{fila.etiqueta}</th>
              {fila.datos.map((punto) => (
                <td key={punto.periodo}>{fila.formatear(punto.valor)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="tabla-fundamentales-fuente">
        Fuente:{" "}
        <a href={fundamentales.fuente_url} target="_blank" rel="noreferrer">
          SEC EDGAR, {fundamentales.periodo} ↗
        </a>
      </p>
    </div>
  );
}
