import type { Historia as HistoriaType } from "../types";
import { formatFechaCorta } from "../lib/format";
import "./Historia.css";

export default function Historia({ historia }: { historia: HistoriaType }) {
  return (
    <article className="historia">
      <h3 className="historia-titulo">{historia.titulo_neutral}</h3>
      <p className="historia-resumen">{historia.resumen}</p>
      {historia.cobertura_unilateral && (
        <p className="historia-unilateral">Cobertura de una sola fuente</p>
      )}
      <ul className="historia-fuentes">
        {historia.articulos.map((articulo) => (
          <li key={articulo.url}>
            <a href={articulo.url} target="_blank" rel="noreferrer">
              {articulo.titular}
            </a>
            <span className="historia-medio">
              [{articulo.medio}
              {articulo.lean !== "no aplica" ? ` · ${articulo.lean}` : ""}]
            </span>
            <time className="historia-fecha" dateTime={articulo.fecha}>
              {formatFechaCorta(articulo.fecha)}
            </time>
          </li>
        ))}
      </ul>
    </article>
  );
}
