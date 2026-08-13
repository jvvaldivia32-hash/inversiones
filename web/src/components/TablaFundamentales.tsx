import { useState } from "react";
import type { Fundamentales, PuntoFundamental } from "../types";
import { formatNumeroCL } from "../lib/format";
import "./TablaFundamentales.css";

interface Fila {
  etiqueta: string;
  datos: PuntoFundamental[];
  formatear: (valor: number) => string;
}

function anioDe(periodo: string): string {
  return periodo.match(/^FY\d+/)?.[0] ?? periodo;
}

export default function TablaFundamentales({
  fundamentales,
}: {
  fundamentales: Fundamentales;
}) {
  const s = fundamentales.series;
  const periodos = s.ingresos_musd.map((p) => p.periodo);
  const anios = [...new Set(periodos.map(anioDe))];
  const [anioSeleccionado, setAnioSeleccionado] = useState(anios[anios.length - 1]);

  const filasCompletas: Fila[] = [
    { etiqueta: "Ingresos", datos: s.ingresos_musd, formatear: (v) => `$${formatNumeroCL(v, 0)}M` },
    { etiqueta: "Operating income", datos: s.op_income_musd, formatear: (v) => `$${formatNumeroCL(v, 0)}M` },
    { etiqueta: "EPS diluido (GAAP)", datos: s.eps_gaap, formatear: (v) => `$${formatNumeroCL(v, 2)}` },
    { etiqueta: "EPS (non-GAAP)", datos: s.eps_non_gaap, formatear: (v) => `$${formatNumeroCL(v, 2)}` },
    { etiqueta: "Margen operativo", datos: s.margen_operativo, formatear: (v) => `${formatNumeroCL(v, 1)}%` },
    { etiqueta: "Capex", datos: s.capex_musd, formatear: (v) => `$${formatNumeroCL(v, 0)}M` },
    { etiqueta: "Flujo operativo", datos: s.flujo_op_musd, formatear: (v) => `$${formatNumeroCL(v, 0)}M` },
  ];

  const filas = filasCompletas
    .map((fila) => ({
      ...fila,
      datos: fila.datos.filter((d) => anioDe(d.periodo) === anioSeleccionado),
    }))
    .filter((fila) => fila.datos.length > 0);

  const periodosVisibles = periodos.filter((p) => anioDe(p) === anioSeleccionado);

  return (
    <div className="tabla-fundamentales-wrap">
      {anios.length > 1 && (
        <div className="tabla-fundamentales-anios" role="group" aria-label="Año fiscal">
          {anios.map((a) => (
            <button
              key={a}
              type="button"
              className={a === anioSeleccionado ? "activo" : ""}
              onClick={() => setAnioSeleccionado(a)}
            >
              {a}
            </button>
          ))}
        </div>
      )}
      <table className="tabla-fundamentales">
        <thead>
          <tr>
            <th></th>
            {periodosVisibles.map((p) => (
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
