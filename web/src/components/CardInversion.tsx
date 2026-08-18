import { useState, type FormEvent } from "react";
import type { EstadoSemaforo, Posicion, RangoPrecio, Segmento, SeriePrecio, Tesis } from "../types";
import { formatPct, formatUSD, formatFechaCorta } from "../lib/format";
import Cifra from "./Cifra";
import Semaforo from "./Semaforo";
import GraficoPrecio from "./GraficoPrecio";
import TablaFundamentales from "./TablaFundamentales";
import MetricasAvanzadas from "./MetricasAvanzadas";
import FormularioTesis from "./FormularioTesis";
import MiInversion, { calcularEnVivo, type MiInversionResumen } from "./MiInversion";
import "./CardInversion.css";

const ORDEN_SEMAFORO: Record<EstadoSemaforo, number> = { rojo: 0, ambar: 1, verde: 2 };

function peorSemaforo(lista: Tesis[] | undefined): EstadoSemaforo | null {
  let peor: EstadoSemaforo | null = null;
  for (const t of lista ?? []) {
    if (t.estado !== "activa") continue;
    const ultima = t.lecturas[t.lecturas.length - 1];
    if (!ultima) continue;
    if (peor === null || ORDEN_SEMAFORO[ultima.semaforo] < ORDEN_SEMAFORO[peor]) {
      peor = ultima.semaforo;
    }
  }
  return peor;
}

function simboloDireccion(direccion: Tesis["direccion"]): { verde: string; rojo: string } {
  return direccion === "mayor_es_mejor" ? { verde: "≥", rojo: "<" } : { verde: "≤", rojo: ">" };
}

function CerrarTesis({ id }: { id: string }) {
  const [abierto, setAbierto] = useState(false);
  const [notas, setNotas] = useState("");
  const [clave, setClave] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cerrada, setCerrada] = useState(false);

  if (cerrada) {
    return <p className="tesis-formulario-ok">Tesis cerrada. Se refleja en la próxima actualización.</p>;
  }

  if (!abierto) {
    return (
      <button type="button" className="tesis-cerrar-abrir" onClick={() => setAbierto(true)}>
        cerrar tesis
      </button>
    );
  }

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      const resp = await fetch("/api/tesis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accion: "cerrar", clave, id, notas_cierre: notas }),
      });
      const data = (await resp.json()) as { error?: string };
      if (!resp.ok) {
        setError(data.error ?? "no se pudo cerrar");
        return;
      }
      setCerrada(true);
    } catch {
      setError("no se pudo conectar");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="tesis-formulario tesis-cerrar-formulario" onSubmit={enviar}>
      <label>
        Por qué se cierra (qué pasó, qué te hizo cambiar de opinión)
        <textarea value={notas} onChange={(e) => setNotas(e.target.value)} required minLength={10} rows={2} />
      </label>
      <label>
        Clave
        <input type="password" value={clave} onChange={(e) => setClave(e.target.value)} required />
      </label>
      {error && <p className="tesis-formulario-error">{error}</p>}
      <div className="tesis-formulario-botones">
        <button type="submit" disabled={enviando}>
          Confirmar cierre
        </button>
        <button type="button" onClick={() => setAbierto(false)} disabled={enviando}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

function TesisItem({ t, fuenteFundamentales }: { t: Tesis; fuenteFundamentales: string }) {
  const [verHistorial, setVerHistorial] = useState(false);
  const ultima = t.lecturas[t.lecturas.length - 1];
  const simbolos = simboloDireccion(t.direccion);

  return (
    <div className="tesis-item">
      <p className="tesis-texto">{t.texto}</p>
      <p className="tesis-metrica">
        {t.metrica_campo}
        {ultima && (
          <>
            :{" "}
            <strong>
              <Cifra
                valor={ultima.valor}
                fuente={ultima.extraido_por === "segmento" ? "Comunicado de prensa (8-K)" : "SEC EDGAR"}
                cita={ultima.cita_textual || undefined}
                url={ultima.fuente_url || fuenteFundamentales}
              />
            </strong>
          </>
        )}{" "}
        (verde {simbolos.verde} {t.umbral_verde}, rojo {simbolos.rojo} {t.umbral_rojo})
      </p>
      {ultima ? (
        <Semaforo estado={ultima.semaforo} />
      ) : (
        <span className="tesis-sin-lectura">sin lecturas todavía — se revisa cuando reporte</span>
      )}
      {t.estado === "cerrada" && t.notas_cierre && (
        <p className="tesis-notas-cierre">Cerrada: {t.notas_cierre}</p>
      )}
      {t.lecturas.length > 0 && (
        <>
          <button
            type="button"
            className="tesis-historial-toggle"
            onClick={() => setVerHistorial((v) => !v)}
          >
            {verHistorial ? "ocultar historial ▴" : `historial (${t.lecturas.length}) ▾`}
          </button>
          {verHistorial && (
            <ul className="tesis-historial">
              {[...t.lecturas].reverse().map((l, i) => (
                <li key={`${l.periodo}-${i}`}>
                  <span className="tesis-historial-periodo">{l.periodo || l.fecha_reporte}</span>
                  <Cifra
                    valor={l.valor}
                    fuente={l.extraido_por === "segmento" ? "8-K" : "SEC EDGAR"}
                    cita={l.cita_textual || undefined}
                    url={l.fuente_url}
                  />
                  <Semaforo estado={l.semaforo} />
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      {t.estado === "activa" && <CerrarTesis id={t.id} />}
    </div>
  );
}

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
          {segmento.detalle.map((d, i) => (
            <SegmentoItem key={`${d.nombre}-${i}`} segmento={d} fuenteUrl={fuenteUrl} />
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
  miInversion: MiInversionResumen | null;
  miInversionCargando: boolean;
  miInversionError: boolean;
  onCambioMiInversion: (ticker: string, datos: MiInversionResumen | null) => void;
}

export default function CardInversion({
  posicion,
  comparables = [],
  miInversion,
  miInversionCargando,
  miInversionError,
  onCambioMiInversion,
}: CardInversionProps) {
  const [expandida, setExpandida] = useState(false);
  const [rango, setRango] = useState<RangoPrecio>("1A");
  const [compararTicker, setCompararTicker] = useState<string | null>(null);
  const [verAvanzadas, setVerAvanzadas] = useState(false);

  const varDiaClase = posicion.var_dia_pct >= 0 ? "var-positiva" : "var-negativa";
  const comparar = comparables.find((c) => c.ticker === compararTicker) ?? null;
  const semaforoHeader = peorSemaforo(posicion.tesis);

  const sinDatosExtra =
    !posicion.fundamentales &&
    !posicion.segmentos &&
    !(posicion.tesis && posicion.tesis.length > 0) &&
    !posicion.noticias;

  const metricasFundamental = posicion.fundamentales
    ? Object.entries(posicion.fundamentales.series)
        .filter(([, serie]) => serie.length > 0)
        .map(([campo]) => campo)
    : [];
  // Gemini a veces extrae el mismo segmento dos veces con cifras distintas (ajustado vs.
// reportado, visto de verdad con MSFT/Microsoft 365 Commercial cloud) — sin un id propio
// por segmento no hay forma de distinguirlas en el dropdown, así que se deduplica por
// nombre y listo.
const metricasSegmento = [...new Set((posicion.segmentos ?? []).map((s) => s.nombre))];

  return (
    <article className="card-inversion">
      <header className="card-inversion-header">
        <h3 className="card-inversion-ticker">{posicion.ticker}</h3>
        <span className="card-inversion-precio">{formatUSD(posicion.precio)}</span>
        <span className={`card-inversion-var ${varDiaClase}`}>
          {formatPct(posicion.var_dia_pct)}
        </span>
        {miInversion && posicion.precio > 0 && (() => {
          const { montoActual, gananciaUsd, gananciaPct } = calcularEnVivo(miInversion, posicion.precio);
          return (
            <span
              className={`card-inversion-var-costo ${gananciaUsd >= 0 ? "var-positiva" : "var-negativa"}`}
            >
              {formatUSD(montoActual)} · {formatPct(gananciaPct)}
            </span>
          );
        })()}
        {semaforoHeader && <Semaforo estado={semaforoHeader} />}
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
        {(posicion.noticias ?? []).slice(0, expandida ? undefined : 2).map((n) => (
          <li key={n.url}>
            <a href={n.url} target="_blank" rel="noreferrer">
              {n.titular}
            </a>
            <span className="card-inversion-medio">[{n.medio}]</span>
            {expandida && n.extracto && <p className="card-inversion-extracto">{n.extracto}</p>}
          </li>
        ))}
      </ul>

      {expandida && (
        <div className="card-inversion-expandida">
          <section>
            <h4>Mi inversión</h4>
            <MiInversion
              ticker={posicion.ticker}
              precioActual={posicion.precio}
              datos={miInversion}
              cargando={miInversionCargando}
              error={miInversionError}
              onGuardado={onCambioMiInversion}
            />
          </section>

          {sinDatosExtra && (
            <p className="card-inversion-sin-datos">
              Sin fundamentales, segmentos, tesis ni noticias para este ticker por ahora —
              por ahora esta card solo tiene precio real.
            </p>
          )}

          {posicion.fundamentales && (
            <section>
              <h4>Fundamentales</h4>
              <TablaFundamentales fundamentales={posicion.fundamentales} />
            </section>
          )}

          {posicion.metricas_avanzadas && (
            <section>
              <button
                type="button"
                className="card-inversion-avanzadas-toggle"
                aria-expanded={verAvanzadas}
                onClick={() => setVerAvanzadas((v) => !v)}
              >
                {verAvanzadas ? "ocultar métricas avanzadas ▴" : "métricas avanzadas ▾"}
              </button>
              {verAvanzadas && <MetricasAvanzadas metricas={posicion.metricas_avanzadas} />}
            </section>
          )}

          {posicion.segmentos && posicion.segmentos.length > 0 && (
            <section>
              <h4>Segmentos</h4>
              <ul className="segmentos">
                {posicion.segmentos.map((s, i) => (
                  <SegmentoItem
                    key={`${s.nombre}-${i}`}
                    segmento={s}
                    fuenteUrl={posicion.segmentos_fuente_url ?? ""}
                  />
                ))}
              </ul>
            </section>
          )}

          {(posicion.tesis && posicion.tesis.length > 0) || metricasFundamental.length > 0 || metricasSegmento.length > 0 ? (
            <section>
              <h4>Tesis</h4>
              {(posicion.tesis ?? []).map((t) => (
                <TesisItem key={t.id} t={t} fuenteFundamentales={posicion.fundamentales?.fuente_url ?? ""} />
              ))}
              {(metricasFundamental.length > 0 || metricasSegmento.length > 0) && (
                <FormularioTesis
                  ticker={posicion.ticker}
                  metricasFundamental={metricasFundamental}
                  metricasSegmento={metricasSegmento}
                  onCreada={() => {}}
                />
              )}
            </section>
          ) : null}

          {posicion.proxima_earnings && (
            <p className="card-inversion-earnings">
              Próxima fecha de resultados: {formatFechaCorta(posicion.proxima_earnings)}
            </p>
          )}
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
