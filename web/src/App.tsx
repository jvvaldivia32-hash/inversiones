import { useEffect, useState } from "react";
import rawDaily from "./data/daily.json";
import type { DailyData } from "./types";
import { formatHora } from "./lib/format";
import Seccion from "./components/Seccion";
import NavBar from "./components/NavBar";
import { SECCION_A_VISTA, type Vista } from "./lib/navegacion";
import Historia from "./components/Historia";
import Actualidad from "./components/Actualidad";
import CardInversion from "./components/CardInversion";
import CardInversionPendiente from "./components/CardInversionPendiente";
import PanelWatchlist from "./components/PanelWatchlist";
import Referencias from "./components/Referencias";
import Radar from "./components/Radar";
import PortafolioFintual from "./components/PortafolioFintual";
import Diccionario from "./components/Diccionario";
import AmigosDemo from "./components/AmigosDemo";
import ErroresFooter from "./components/ErroresFooter";
import EstadoMercado from "./components/EstadoMercado";
import "./App.css";

const daily = rawDaily as unknown as DailyData;

function vistaDesdeHash(): Vista {
  const id = window.location.hash.replace("#", "");
  return SECCION_A_VISTA[id] ?? "dia";
}

function App() {
  const [watchlist, setWatchlist] = useState<string[] | null>(null);
  const [watchlistError, setWatchlistError] = useState(false);
  const [vista, setVista] = useState<Vista>(vistaDesdeHash);

  useEffect(() => {
    fetch("/api/watchlist")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json() as Promise<{ tickers: string[] }>;
      })
      .then((data) => setWatchlist(data.tickers))
      .catch(() => setWatchlistError(true));
  }, []);

  // Primer scroll al cargar, si la URL ya apuntaba a una sección específica.
  useEffect(() => {
    const id = window.location.hash.replace("#", "");
    if (id) document.getElementById(id)?.scrollIntoView({ block: "start" });
  }, []);

  useEffect(() => {
    const alCambiarHash = () => setVista(vistaDesdeHash());
    window.addEventListener("hashchange", alCambiarHash);
    return () => window.removeEventListener("hashchange", alCambiarHash);
  }, []);

  function irA(id: string) {
    const vistaDestino = SECCION_A_VISTA[id] ?? "dia";
    const cambiaVista = vistaDestino !== vista;
    if (cambiaVista) setVista(vistaDestino);
    window.location.hash = id;

    const sinMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const scrollear = () =>
      document
        .getElementById(id)
        ?.scrollIntoView({ block: "start", behavior: sinMovimiento ? "auto" : "smooth" });

    // Si cambia de vista, la sección destino recién se monta en este render — hay que
    // esperar al siguiente frame pintado antes de poder scrollear hasta ella.
    if (cambiaVista) {
      requestAnimationFrame(() => requestAnimationFrame(scrollear));
    } else {
      scrollear();
    }
  }

  const posicionesVisibles =
    watchlist === null
      ? daily.posiciones
      : daily.posiciones.filter((p) => watchlist.includes(p.ticker));

  const pendientes =
    watchlist === null
      ? []
      : watchlist.filter((t) => !daily.posiciones.some((p) => p.ticker === t));

  return (
    <>
      <header className="app-header">
        <p>Actualizado hoy {formatHora(daily.generado)}</p>
        <EstadoMercado />
      </header>

      <NavBar vista={vista} onIrA={irA} />

      {vista === "dia" && (
        <>
          <Seccion id="referencias" titulo="Referencias" compacta>
            <Referencias referencias={daily.referencias} />
          </Seccion>

          <Seccion id="mundo" titulo="Mundo">
            {daily.bloques.mundo.map((h) => (
              <Historia key={h.titulo_neutral} historia={h} />
            ))}
          </Seccion>

          <Seccion id="chile" titulo="Chile">
            {daily.bloques.chile.map((h) => (
              <Historia key={h.titulo_neutral} historia={h} />
            ))}
          </Seccion>

          <Seccion id="actualidad" titulo="Actualidad" compacta>
            <Actualidad items={daily.bloques.actualidad} />
          </Seccion>
        </>
      )}

      {vista === "inversion" && (
        <>
          {daily.fintual && (
            <Seccion id="fintual" titulo="Mi portafolio" compacta>
              <PortafolioFintual fintual={daily.fintual} />
            </Seccion>
          )}

          <Seccion id="mis-inversiones" titulo="Mis inversiones">
            <div className="posiciones-lista">
              {posicionesVisibles.map((p) => (
                <CardInversion
                  key={p.ticker}
                  posicion={p}
                  comparables={posicionesVisibles
                    .filter((otra) => otra.ticker !== p.ticker)
                    .map((otra) => ({ ticker: otra.ticker, serie: otra.serie_precio }))}
                />
              ))}
              {pendientes.map((t) => (
                <CardInversionPendiente key={t} ticker={t} />
              ))}
            </div>
            <PanelWatchlist
              watchlist={watchlist}
              error={watchlistError}
              onChange={setWatchlist}
            />
          </Seccion>

          <Seccion id="radar" titulo="En el radar" compacta>
            <Radar radar={daily.radar} watchlist={watchlist} />
          </Seccion>
        </>
      )}

      {vista === "diccionario" && (
        <Seccion id="diccionario" titulo="Diccionario" compacta>
          <Diccionario />
        </Seccion>
      )}

      {vista === "amigos" && (
        <Seccion id="amigos" titulo="Amigos" compacta>
          <AmigosDemo />
        </Seccion>
      )}

      <ErroresFooter errores={daily.errores} />
    </>
  );
}

export default App;
