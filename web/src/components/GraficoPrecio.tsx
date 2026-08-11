import { useId } from "react";
import {
  Area,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PuntoPrecio, RangoPrecio, SeriePrecio } from "../types";
import { formatFechaCorta, formatUSD } from "../lib/format";
import "./GraficoPrecio.css";

const RANGOS: RangoPrecio[] = ["1M", "6M", "YTD", "1A", "5A"];

function formatEjeY(valor: number): string {
  return `US$${Math.round(valor).toLocaleString("es-CL")}`;
}

function formatPct(valor: number): string {
  return `${valor > 0 ? "+" : ""}${valor.toFixed(1)}%`;
}

function normalizarPct(datos: PuntoPrecio[]): PuntoPrecio[] {
  if (datos.length === 0) return [];
  const base = datos[0].valor;
  return datos.map((d) => ({ fecha: d.fecha, valor: ((d.valor - base) / base) * 100 }));
}

interface PuntoComparado {
  fecha: string;
  principal: number | null;
  comparado: number | null;
}

function combinarComparacion(principal: PuntoPrecio[], comparado: PuntoPrecio[]): PuntoComparado[] {
  const porFecha = new Map<string, PuntoComparado>();
  for (const p of normalizarPct(principal)) {
    porFecha.set(p.fecha, { fecha: p.fecha, principal: p.valor, comparado: null });
  }
  for (const c of normalizarPct(comparado)) {
    const existente = porFecha.get(c.fecha);
    if (existente) existente.comparado = c.valor;
    else porFecha.set(c.fecha, { fecha: c.fecha, principal: null, comparado: c.valor });
  }
  return [...porFecha.values()].sort((a, b) => a.fecha.localeCompare(b.fecha));
}

interface SelectorRangoProps {
  rango: RangoPrecio;
  onRangoChange?: (rango: RangoPrecio) => void;
}

function SelectorRango({ rango, onRangoChange }: SelectorRangoProps) {
  return (
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
  );
}

interface GraficoPrecioProps {
  serie: SeriePrecio;
  rango: RangoPrecio;
  onRangoChange?: (rango: RangoPrecio) => void;
  mostrarSelector?: boolean;
  comparar?: { ticker: string; serie: SeriePrecio } | null;
}

const tooltipEstilo = {
  fontSize: 12,
  fontFamily: "var(--fuente-mono)",
  border: "1px solid var(--linea)",
  borderRadius: 4,
};

const ejeTick = { fontSize: 11, fill: "var(--tinta-suave)" };

export default function GraficoPrecio({
  serie,
  rango,
  onRangoChange,
  mostrarSelector = false,
  comparar,
}: GraficoPrecioProps) {
  const idGradiente = `grafico-degradado-${useId()}`;
  const datos = serie[rango];

  if (comparar) {
    const datosComparados = combinarComparacion(datos, comparar.serie[rango]);
    return (
      <div className="grafico-precio">
        {mostrarSelector && <SelectorRango rango={rango} onRangoChange={onRangoChange} />}
        <ResponsiveContainer width="100%" height={120}>
          <ComposedChart data={datosComparados} margin={{ top: 4, right: 8, bottom: 0, left: 4 }}>
            <XAxis
              dataKey="fecha"
              tickFormatter={formatFechaCorta}
              tick={ejeTick}
              axisLine={{ stroke: "var(--linea)" }}
              tickLine={false}
              minTickGap={30}
            />
            <YAxis
              domain={["auto", "auto"]}
              tickFormatter={formatPct}
              tick={ejeTick}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <Tooltip
              formatter={(valor) => formatPct(Number(valor))}
              labelFormatter={(label) => formatFechaCorta(String(label))}
              contentStyle={tooltipEstilo}
            />
            <Line
              type="monotone"
              dataKey="principal"
              stroke="var(--acento)"
              strokeWidth={2}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="comparado"
              stroke="var(--acento)"
              strokeWidth={2}
              strokeDasharray="5 4"
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
        <p className="grafico-leyenda">
          <span className="grafico-leyenda-linea grafico-leyenda-linea--solida" />
          serie principal
          <span className="grafico-leyenda-linea grafico-leyenda-linea--punteada" />
          {comparar.ticker}
        </p>
      </div>
    );
  }

  return (
    <div className="grafico-precio">
      {mostrarSelector && <SelectorRango rango={rango} onRangoChange={onRangoChange} />}
      <ResponsiveContainer width="100%" height={120}>
        <ComposedChart data={datos} margin={{ top: 4, right: 8, bottom: 0, left: 4 }}>
          <defs>
            <linearGradient id={idGradiente} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--acento)" stopOpacity={0.28} />
              <stop offset="100%" stopColor="var(--acento)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="fecha"
            tickFormatter={formatFechaCorta}
            tick={ejeTick}
            axisLine={{ stroke: "var(--linea)" }}
            tickLine={false}
            minTickGap={30}
          />
          <YAxis
            domain={["auto", "auto"]}
            tickFormatter={formatEjeY}
            tick={ejeTick}
            axisLine={false}
            tickLine={false}
            width={78}
          />
          <Tooltip
            formatter={(valor) => formatUSD(Number(valor))}
            labelFormatter={(label) => formatFechaCorta(String(label))}
            contentStyle={tooltipEstilo}
          />
          <Area
            type="monotone"
            dataKey="valor"
            stroke="var(--acento)"
            strokeWidth={2}
            fill={`url(#${idGradiente})`}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
