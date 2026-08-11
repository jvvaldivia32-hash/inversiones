import rawDaily from "./data/daily.json";
import type { DailyData } from "./types";
import { formatHora } from "./lib/format";
import Seccion from "./components/Seccion";
import Historia from "./components/Historia";
import Actualidad from "./components/Actualidad";
import CardInversion from "./components/CardInversion";
import Referencias from "./components/Referencias";
import Radar from "./components/Radar";
import ErroresFooter from "./components/ErroresFooter";
import "./App.css";

const daily = rawDaily as unknown as DailyData;

function App() {
  return (
    <>
      <header className="app-header">
        <p>Actualizado hoy {formatHora(daily.generado)}</p>
      </header>

      <Seccion titulo="Mundo">
        {daily.bloques.mundo.map((h) => (
          <Historia key={h.titulo_neutral} historia={h} />
        ))}
      </Seccion>

      <Seccion titulo="Chile">
        {daily.bloques.chile.map((h) => (
          <Historia key={h.titulo_neutral} historia={h} />
        ))}
      </Seccion>

      <Seccion titulo="Actualidad" compacta>
        <Actualidad items={daily.bloques.actualidad} />
      </Seccion>

      <Seccion titulo="Mis inversiones">
        <div className="posiciones-lista">
          {daily.posiciones.map((p) => (
            <CardInversion key={p.ticker} posicion={p} />
          ))}
        </div>
      </Seccion>

      <Seccion titulo="Referencias" compacta>
        <Referencias referencias={daily.referencias} />
      </Seccion>

      <Seccion titulo="En el radar" compacta>
        <Radar radar={daily.radar} />
      </Seccion>

      <ErroresFooter errores={daily.errores} />
    </>
  );
}

export default App;
