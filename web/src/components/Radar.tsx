import type { RadarData } from "../types";
import "./Radar.css";

export default function Radar({ radar }: { radar: RadarData }) {
  return (
    <div className="radar">
      <div className="radar-bloque">
        <h4>Candidatos</h4>
        <ul className="radar-candidatos">
          {radar.candidatos.map((c) => (
            <li key={c.ticker}>
              <div className="radar-candidato-header">
                <span className="radar-ticker">{c.ticker}</span>
                <span className="radar-nombre">{c.nombre}</span>
                <span className="radar-pct">{c.pct_bajo_maximo}% bajo su máximo</span>
              </div>
              <p className="radar-motivo">{c.motivo}</p>
            </li>
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
