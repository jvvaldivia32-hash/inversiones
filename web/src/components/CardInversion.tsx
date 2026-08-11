import { useState } from "react";
import type { Posicion, RangoPrecio, Segmento, SeriePrecio } from "../types";
import { formatPct, formatUSD, formatFechaCorta } from "../lib/format";
import Cifra from "./Cifra";
import Semaforo from "./Semaforo";
import GraficoPrecio from "./GraficoPrecio";
import TablaFundamentales from "./TablaFundamentales";
import "./CardInversion.css";

function SegmentoItem({ segmento, fuenteUrl }: { segmento: Segmento; fuenteUrl: string }) {
  return (
    <li className="segmento">
      <span className="segmento-nombre">{segmento.nombre}</span>
      <span className={segmento.var_pct >= 0 ? "var-positiva" : "var-negativa"}>
        <Cifra
          valor={formatPct(segmento.var_pct, 0)}
          fuente="Comunicado de prensa (8-K)"
          cita={segmento.cita}
          url={fuenteUrl}
        />
      </span>
      {segmento.detalle && segmento.detalle.length > 0 && (
        <ul className="segmento-detalle">
          {segmento.detalle.map((d) => (
            <SegmentoItem key={d.nombre} segmento={d} fuenteUrl={fuenteUrl} />
          ))}
        </ul>
      )}
    </li>
  );
}

interface Comparable {
  ticker: string;
  serie: SeriePrecio;
}

interface CardInversionProps {
  posicion: Posicion;
  comparables?: Comparable[];
}

export default function CardInversion({ posicion, comparables = [] }: CardInversionProps) {
  const [expandida, setExpandida] = useState(false);
  const [rango, setRango] = useState<RangoPrecio>("1A");
  const [compararTicker, setCompararTicker] = useState<string | null>(null);

  const varDiaClase = posicion.var_dia_pct >= 0 ? "var-positiva" : "var-negativa";
  const varAnoClase = posicion.var_ano_pct >= 0 ? "var-positiva" : "var-negativa";
  const comparar = comparables.find((c) => c.ticker === compararTicker) ?? null;

  return (
    <article className="card-inversion">
      <header className="card-inversion-header">
        <h3 className="card-inversion-ticker">{posicion.ticker}</h3>
        <span className="card-inversion-precio">{formatUSD(posicion.precio)}</span>
        <span className={`card-inversion-var ${varDiaClase}`}>
          {formatPct(posicion.var_dia_pct)}
        </span>
        <span className={`card-inversion-var-costo ${varAnoClase}`}>
          {formatPct(posicion.var_ano_pct)} desde costo
        </span>
        <Semaforo estado={posicion.tesis.semaforo} />
      </header>

      <GraficoPrecio
        serie={posicion.serie_precio}
        rango={expandida ? rango : "1A"}
        onRangoChange={setRango}
        mostrarSelector={expandida}
        comparar={comparar}
      />

      {expandida && comparables.length > 0 && (
        <div className="card-inversion-comparar" role="group" aria-label="Comparar con">
          <span className="card-inversion-comparar-etiqueta">comparar con:</span>
          {comparables.map((c) => (
            <button
              key={c.ticker}
              type="button"
              className={c.ticker === compararTicker ? "activo" : ""}
              onClick={() =>
                setCompararTicker((actual) => (actual === c.ticker ? null : c.ticker))
              }
            >
              {c.ticker}
            </button>
          ))}
        </div>
      )}

      <ul className="card-inversion-titulares">
        {posicion.noticias.slice(0, expandida ? posicion.noticias.length : 2).map((n) => (
          <li key={n.url}>
            <a href={n.url} target="_blank" rel="noreferrer">
              {n.titular}
            </a>
            <span className="card-inversion-medio">[{n.medio}]</span>
            {expandida && <p className="card-inversion-extracto">{n.extracto}</p>}
          </li>
        ))}
      </ul>

      {expandida && (
        <div className="card-inversion-expandida">
          <section>
            <h4>Fundamentales</h4>
            <TablaFundamentales fundamentales={posicion.fundamentales} />
          </section>

          <section>
            <h4>Segmentos</h4>
            <ul className="segmentos">
              {posicion.segmentos.map((s) => (
                <SegmentoItem
                  key={s.nombre}
                  segmento={s}
                  fuenteUrl={posicion.fundamentales.fuente_url}
                />
              ))}
            </ul>
          </section>

          <section>
            <h4>Tesis</h4>
            <p className="tesis-texto">{posicion.tesis.texto}</p>
            <p className="tesis-metrica">
              {posicion.tesis.metrica}: <strong>{posicion.tesis.valor_actual}</strong>{" "}
              (verde ≥ {posicion.tesis.umbral_verde}, rojo &lt; {posicion.tesis.umbral_rojo})
            </p>
            <Semaforo estado={posicion.tesis.semaforo} />
          </section>

          <p className="card-inversion-earnings">
            Próxima fecha de resultados: {formatFechaCorta(posicion.proxima_earnings)}
          </p>
        </div>
      )}

      <button
        type="button"
        className="card-inversion-toggle"
        onClick={() => setExpandida((v) => !v)}
        aria-expanded={expandida}
      >
        {expandida ? "cerrar ▴" : "abrir ▾"}
      </button>
    </article>
  );
}
