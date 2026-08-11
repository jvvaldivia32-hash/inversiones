import { useEffect, useState } from "react";
import rawDaily from "./data/daily.json";
import type { DailyData } from "./types";
import { formatHora } from "./lib/format";
import Seccion from "./components/Seccion";
import NavBar from "./components/NavBar";
import Historia from "./components/Historia";
import Actualidad from "./components/Actualidad";
import CardInversion from "./components/CardInversion";
import CardInversionPendiente from "./components/CardInversionPendiente";
import PanelWatchlist from "./components/PanelWatchlist";
import Referencias from "./components/Referencias";
import Radar from "./components/Radar";
import ErroresFooter from "./components/ErroresFooter";
import "./App.css";

const daily = rawDaily as unknown as DailyData;

function App() {
  const [watchlist, setWatchlist] = useState<string[] | null>(null);
  const [watchlistError, setWatchlistError] = useState(false);

  useEffect(() => {
    fetch("/api/watchlist")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json() as Promise<{ tickers: string[] }>;
      })
      .then((data) => setWatchlist(data.tickers))
      .catch(() => setWatchlistError(true));
  }, []);

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
      </header>

      <NavBar />

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

      <Seccion id="mis-inversiones" titulo="Mis inversiones">
        <div className="posiciones-lista">
          {posicionesVisibles.map((p) => (
            <CardInversion key={p.ticker} posicion={p} />
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

      <Seccion id="referencias" titulo="Referencias" compacta>
        <Referencias referencias={daily.referencias} />
      </Seccion>

      <Seccion id="radar" titulo="En el radar" compacta>
        <Radar radar={daily.radar} />
      </Seccion>

      <ErroresFooter errores={daily.errores} />
    </>
  );
}

export default App;
