import { useEffect, useState } from "react";
import type { PaperInvestingResumen, RangoPrecio } from "../types";
import type { PrecioDisponible } from "../lib/preciosDisponibles";
import { formatUSD, formatPct } from "../lib/format";
import MiInversion, { calcularEnVivo } from "./MiInversion";
import GraficoPrecio from "./GraficoPrecio";
import "./PaperInvesting.css";

const ENDPOINT = "/api/paperinvesting";

interface Props {
  precios: Record<string, PrecioDisponible>;
}

function CardPosicionPapel({
  ticker,
  precio,
  datos,
  onCambio,
}: {
  ticker: string;
  precio: PrecioDisponible | undefined;
  datos: PaperInvestingResumen["posiciones"][string];
  onCambio: (ticker: string, datos: PaperInvestingResumen["posiciones"][string] | null) => void;
}) {
  const [rango, setRango] = useState<RangoPrecio>("1A");

  return (
    <article className="paper-posicion">
      <header className="paper-posicion-header">
        <h3>{ticker}</h3>
        {precio && <span>{formatUSD(precio.precio)}</span>}
      </header>
      {precio ? (
        <GraficoPrecio
          serie={precio.serie_precio}
          rango={rango}
          onRangoChange={setRango}
          mostrarSelector
        />
      ) : (
        <p className="paper-posicion-sin-precio">
          Sin precio actualizado esta semana (dejó de aparecer en watchlist/candidatos del
          Radar) — se recalcula apenas vuelva a tener dato fresco.
        </p>
      )}
      <MiInversion
        ticker={ticker}
        precioActual={precio?.precio ?? 0}
        datos={datos}
        cargando={false}
        error={false}
        onGuardado={onCambio}
        endpoint={ENDPOINT}
        permitirEditar={false}
      />
    </article>
  );
}

export default function PaperInvesting({ precios }: Props) {
  const [estado, setEstado] = useState<PaperInvestingResumen | null>(null);
  const [error, setError] = useState(false);
  const [busqueda, setBusqueda] = useState("");

  useEffect(() => {
    fetch(ENDPOINT)
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json() as Promise<PaperInvestingResumen>;
      })
      .then(setEstado)
      .catch(() => setError(true));
  }, []);

  // El endpoint mueve el efectivo del lado del servidor (comprar resta, vender suma) — en
  // vez de reconstruir ese cálculo en el cliente, se vuelve a pedir el archivo completo
  // tras cada compra/venta. Es una app de un solo usuario con clave compartida, no hay
  // volumen de tráfico que justifique optimizar esto.
  function alCambiar() {
    fetch(ENDPOINT)
      .then((r) => (r.ok ? (r.json() as Promise<PaperInvestingResumen>) : null))
      .then((data) => data && setEstado(data));
  }

  if (error) {
    return <p className="paper-investing-error">No se pudo cargar el simulador ahora.</p>;
  }
  if (!estado) {
    return <p className="paper-investing-nota">cargando…</p>;
  }

  const totalAportado = 5000 + estado.aportes.reduce((acc, a) => acc + a.monto_usd, 0);
  const valorPosiciones = Object.entries(estado.posiciones).reduce((acc, [ticker, datos]) => {
    const precio = precios[ticker];
    if (!precio) return acc;
    return acc + calcularEnVivo(datos, precio.precio).montoActual;
  }, 0);
  const valorTotal = estado.saldo_no_invertido_usd + valorPosiciones;
  const gananciaPct = ((valorTotal - totalAportado) / totalAportado) * 100;

  const resultados = busqueda.trim()
    ? Object.values(precios).filter(
        (p) =>
          p.ticker.toLowerCase().includes(busqueda.trim().toLowerCase()) ||
          p.nombre.toLowerCase().includes(busqueda.trim().toLowerCase()),
      )
    : [];

  return (
    <div className="paper-investing">
      <ul className="paper-investing-resumen">
        <li>
          <span>Efectivo disponible</span>
          <strong>{formatUSD(estado.saldo_no_invertido_usd)}</strong>
        </li>
        <li>
          <span>Aportado en total</span>
          <strong>{formatUSD(totalAportado)}</strong>
        </li>
        <li>
          <span>Valor total hoy</span>
          <strong>{formatUSD(valorTotal)}</strong>
        </li>
        <li className={gananciaPct >= 0 ? "var-positiva" : "var-negativa"}>
          <span>Ganancia</span>
          <strong>{formatPct(gananciaPct)}</strong>
        </li>
      </ul>
      <p className="paper-investing-nota">
        Empezaste el {estado.fecha_inicio} con US$5.000 ficticios + US$100/mes simulado.
        Plata de mentira, precios reales.
      </p>

      <div className="paper-investing-buscador">
        <label>
          Comprar algo nuevo (de tu watchlist o los candidatos del Radar)
          <input
            type="text"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="ticker o nombre"
          />
        </label>
        {resultados.length > 0 && (
          <ul className="paper-investing-resultados">
            {resultados.map((p) => (
              <li key={p.ticker}>
                <span>
                  {p.ticker} — {p.nombre} ({formatUSD(p.precio)})
                </span>
                <MiInversion
                  ticker={p.ticker}
                  precioActual={p.precio}
                  datos={estado.posiciones[p.ticker] ?? null}
                  cargando={false}
                  error={false}
                  onGuardado={alCambiar}
                  endpoint={ENDPOINT}
                  permitirEditar={false}
                />
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="paper-investing-posiciones">
        {Object.entries(estado.posiciones).map(([ticker, datos]) => (
          <CardPosicionPapel
            key={ticker}
            ticker={ticker}
            precio={precios[ticker]}
            datos={datos}
            onCambio={alCambiar}
          />
        ))}
        {Object.keys(estado.posiciones).length === 0 && (
          <p className="paper-investing-nota">
            Todavía no compraste nada — buscá un ticker arriba para empezar.
          </p>
        )}
      </div>
    </div>
  );
}
