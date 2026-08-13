import { useState } from "react";
import type { RadarCandidato, RadarData, RangoPrecio } from "../types";
import GraficoPrecio from "./GraficoPrecio";
import "./Radar.css";

function CandidatoItem({ candidato }: { candidato: RadarCandidato }) {
  const [rango, setRango] = useState<RangoPrecio>("1A");
  const [expandida, setExpandida] = useState(false);

  return (
    <li>
      <div className="radar-candidato-header">
        <span className="radar-ticker">{candidato.ticker}</span>
        <span className="radar-nombre">{candidato.nombre}</span>
        <span className="radar-pct">{candidato.pct_bajo_maximo}% bajo su máximo</span>
      </div>
      <p className="radar-motivo">{candidato.motivo}</p>
      {expandida && (
        <GraficoPrecio
          serie={candidato.serie_precio}
          rango={rango}
          onRangoChange={setRango}
          mostrarSelector
        />
      )}
      <button
        type="button"
        className="radar-candidato-toggle"
        onClick={() => setExpandida((v) => !v)}
        aria-expanded={expandida}
      >
        {expandida ? "cerrar ▴" : "ver gráfico ▾"}
      </button>
    </li>
  );
}

export default function Radar({ radar }: { radar: RadarData }) {
  return (
    <div className="radar">
      <div className="radar-bloque">
        <h4>Candidatos</h4>
        <ul className="radar-candidatos">
          {radar.candidatos.map((c) => (
            <CandidatoItem key={c.ticker} candidato={c} />
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
