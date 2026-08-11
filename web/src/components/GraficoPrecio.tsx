import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { RangoPrecio, SeriePrecio } from "../types";
import { formatFechaCorta, formatUSD } from "../lib/format";
import "./GraficoPrecio.css";

const RANGOS: RangoPrecio[] = ["1M", "6M", "1A", "5A"];

function formatEjeY(valor: number): string {
  return `US$${Math.round(valor).toLocaleString("es-CL")}`;
}

interface GraficoPrecioProps {
  serie: SeriePrecio;
  rango: RangoPrecio;
  onRangoChange?: (rango: RangoPrecio) => void;
  mostrarSelector?: boolean;
}

export default function GraficoPrecio({
  serie,
  rango,
  onRangoChange,
  mostrarSelector = false,
}: GraficoPrecioProps) {
  const datos = serie[rango];

  return (
    <div className="grafico-precio">
      {mostrarSelector && (
        <div className="grafico-selector" role="group" aria-label="Rango del gráfico">
          {RANGOS.map((r) => (
            <button
              key={r}
              type="button"
              className={r === rango ? "activo" : ""}
              onClick={() => onRangoChange?.(r)}
            >
              {r}
            </button>
          ))}
        </div>
      )}
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={datos} margin={{ top: 4, right: 8, bottom: 0, left: 4 }}>
          <XAxis
            dataKey="fecha"
            tickFormatter={formatFechaCorta}
            tick={{ fontSize: 11, fill: "var(--tinta-suave)" }}
            axisLine={{ stroke: "var(--linea)" }}
            tickLine={false}
            minTickGap={30}
          />
          <YAxis
            domain={["auto", "auto"]}
            tickFormatter={formatEjeY}
            tick={{ fontSize: 11, fill: "var(--tinta-suave)" }}
            axisLine={false}
            tickLine={false}
            width={78}
          />
          <Tooltip
            formatter={(valor) => formatUSD(Number(valor))}
            labelFormatter={(label) => formatFechaCorta(String(label))}
            contentStyle={{
              fontSize: 12,
              fontFamily: "var(--fuente-mono)",
              border: "1px solid var(--linea)",
              borderRadius: 4,
            }}
          />
          <Line
            type="monotone"
            dataKey="valor"
            stroke="var(--acento)"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
