import { useEffect, useState } from "react";
import type { RadarCandidato, RadarData, RangoPrecio, Tesis } from "../types";
import GraficoPrecio from "./GraficoPrecio";
import SenalMetrica from "./SenalMetrica";
import {
  contextoCrecimientoIngresos,
  contextoMargenOperativo,
  contextoDeudaPatrimonio,
} from "../lib/referenciasMetricas";
import "./Radar.css";

interface PuertaInversionProps {
  ticker: string;
  enWatchlist: boolean;
  tesisActiva: boolean;
}

function PuertaInversion({ ticker, enWatchlist, tesisActiva }: PuertaInversionProps) {
  if (tesisActiva) {
    // Sin URL real de broker todavía (pendiente que el usuario la pase) — placeholder
    // deshabilitado a propósito, no un link que parezca funcionar y no vaya a ningún lado.
    return (
      <span className="radar-broker-link" title="Falta configurar la URL real del broker">
        ir al broker (falta configurar el link)
      </span>
    );
  }
  if (!enWatchlist) {
    return (
      <p className="radar-puerta-mensaje">
        Agregalo a tu watchlist en «Mis inversiones» para poder escribirle una tesis.
      </p>
    );
  }
  return (
    <p className="radar-puerta-mensaje">
      Sin tesis escrita todavía — abrí la card de {ticker} en «Mis inversiones» y escribí
      una antes de invertir.
    </p>
  );
}

function CandidatoItem({
  candidato,
  enWatchlist,
  tesisActiva,
}: {
  candidato: RadarCandidato;
  enWatchlist: boolean;
  tesisActiva: boolean;
}) {
  const [rango, setRango] = useState<RangoPrecio>("1A");
  const [expandida, setExpandida] = useState(false);
  const [mostrarPuerta, setMostrarPuerta] = useState(false);

  return (
    <li>
      <div className="radar-candidato-header">
        <span className="radar-ticker">{candidato.ticker}</span>
        <span className="radar-nombre">{candidato.nombre}</span>
        <span className="radar-pct">{candidato.pct_bajo_maximo}% bajo su máximo</span>
      </div>
      <p className="radar-motivo">{candidato.motivo}</p>
      {expandida && (
        <>
          <GraficoPrecio
            serie={candidato.serie_precio}
            rango={rango}
            onRangoChange={setRango}
            mostrarSelector
          />
          <ul className="radar-candidato-contexto">
            <li>
              Ingresos:{" "}
              <SenalMetrica
                lectura={contextoCrecimientoIngresos(candidato.metricas.ingresos_var_pct)}
              />
            </li>
            <li>
              Margen operativo:{" "}
              <SenalMetrica lectura={contextoMargenOperativo(candidato.metricas.margen_op)} />
            </li>
            {candidato.metricas.deuda_patrimonio !== null && (
              <li>
                Deuda/patrimonio:{" "}
                <SenalMetrica
                  lectura={contextoDeudaPatrimonio(candidato.metricas.deuda_patrimonio)}
                />
              </li>
            )}
          </ul>
        </>
      )}
      {mostrarPuerta && (
        <PuertaInversion ticker={candidato.ticker} enWatchlist={enWatchlist} tesisActiva={tesisActiva} />
      )}
      <div className="radar-candidato-acciones">
        <button
          type="button"
          className="radar-candidato-toggle"
          onClick={() => setExpandida((v) => !v)}
          aria-expanded={expandida}
        >
          {expandida ? "cerrar ▴" : "ver gráfico ▾"}
        </button>
        <button type="button" className="radar-candidato-toggle" onClick={() => setMostrarPuerta((v) => !v)}>
          invertir
        </button>
      </div>
    </li>
  );
}

export default function Radar({ radar, watchlist }: { radar: RadarData; watchlist: string[] | null }) {
  const [tesisActivasPorTicker, setTesisActivasPorTicker] = useState<Record<string, boolean>>({});

  useEffect(() => {
    fetch("/api/tesis")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json() as Promise<{ tesis: Tesis[] }>;
      })
      .then((data) => {
        const activas: Record<string, boolean> = {};
        for (const t of data.tesis) {
          if (t.estado === "activa") activas[t.ticker] = true;
        }
        setTesisActivasPorTicker(activas);
      })
      .catch(() => {
        // sin bloquear el radar si /api/tesis falla — la puerta de entrada simplemente
        // no sabrá que ya hay una tesis activa, no es un dato crítico para ver el radar.
      });
  }, []);

  return (
    <div className="radar">
      <div className="radar-bloque">
        <h4>Candidatos</h4>
        <ul className="radar-candidatos">
          {radar.candidatos.map((c) => (
            <CandidatoItem
              key={c.ticker}
              candidato={c}
              enWatchlist={watchlist?.includes(c.ticker) ?? false}
              tesisActiva={!!tesisActivasPorTicker[c.ticker]}
            />
          ))}
        </ul>
      </div>

      <div className="radar-bloque">
        <h4>Descartados</h4>
        <ul className="radar-descartados">
          {radar.descartados.map((d) => (
            <li key={d.ticker}>
              <span className="radar-ticker">{d.ticker}</span>
              <span className="radar-pct">{d.pct_bajo_maximo}% bajo su máximo</span>
              <span className="radar-motivo-descarte">Descartada: {d.motivo_descarte}</span>
            </li>
          ))}
        </ul>
      </div>

      <p className="radar-corrida">Última corrida: {radar.ultima_corrida}</p>
    </div>
  );
}
