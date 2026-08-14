import { formatPct, formatUSD } from "../lib/format";
import "./AmigosDemo.css";

/**
 * DEMO — nada de esto es real todavía. Datos inventados a mano para probar dos ideas de
 * cómo se vería "Amigos" antes de decidir cuál construir de verdad:
 *   - Amigo 1: eligió tickers propios, mini recap de precio (sin fundamentales/segmentos/
 *     tesis/noticias — infinitamente más chico que "Mis inversiones").
 *   - Amigo 2: eligió una palabra clave en vez de tickers, mini recap de un par de
 *     titulares de ejemplo relacionados.
 * Ningún dato acá sale de Finnhub/Gemini/EDGAR ni de ninguna API real — es a propósito,
 * para no gastar cuota de nadie mientras se decide el diseño.
 */

interface AmigoTickerDemo {
  ticker: string;
  precio: number;
  var_dia_pct: number;
}

interface AmigoDemo {
  nombre: string;
  modo: "tickers" | "palabra_clave";
  tickers?: AmigoTickerDemo[];
  palabraClave?: string;
  titularesFalsos?: { titular: string; medio: string }[];
}

const AMIGOS_DEMO: AmigoDemo[] = [
  {
    nombre: "Amigo 1",
    modo: "tickers",
    tickers: [
      { ticker: "NVDA", precio: 187.32, var_dia_pct: 1.8 },
      { ticker: "TSLA", precio: 412.1, var_dia_pct: -2.3 },
    ],
  },
  {
    nombre: "Amigo 2",
    modo: "palabra_clave",
    palabraClave: "baterías de litio",
    titularesFalsos: [
      { titular: "Precio del litio sube por primera vez en dos años [ejemplo]", medio: "Medio ejemplo" },
      { titular: "Nueva planta de baterías anunciada en el norte de Chile [ejemplo]", medio: "Medio ejemplo" },
    ],
  },
];

function MiniTicker({ t }: { t: AmigoTickerDemo }) {
  const clase = t.var_dia_pct >= 0 ? "var-positiva" : "var-negativa";
  return (
    <div className="amigos-demo-ticker">
      <span className="amigos-demo-ticker-simbolo">{t.ticker}</span>
      <span>{formatUSD(t.precio)}</span>
      <span className={clase}>{formatPct(t.var_dia_pct)}</span>
    </div>
  );
}

function AmigoCard({ amigo }: { amigo: AmigoDemo }) {
  return (
    <div className="amigos-demo-card">
      <h5>{amigo.nombre}</h5>
      {amigo.modo === "tickers" ? (
        <>
          <p className="amigos-demo-modo">sigue tickers propios</p>
          {(amigo.tickers ?? []).map((t) => (
            <MiniTicker key={t.ticker} t={t} />
          ))}
        </>
      ) : (
        <>
          <p className="amigos-demo-modo">
            sigue la palabra clave "<strong>{amigo.palabraClave}</strong>"
          </p>
          <ul className="amigos-demo-titulares">
            {(amigo.titularesFalsos ?? []).map((n) => (
              <li key={n.titular}>
                {n.titular} <span className="amigos-demo-medio">[{n.medio}]</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export default function AmigosDemo() {
  return (
    <div className="amigos-demo">
      <p className="amigos-demo-aviso">
        Demo con datos inventados — todavía no hay nada real conectado acá. Sirve para
        decidir cómo se debería ver antes de construirlo (login de invitado, límites para
        no gastar API propia, etc.).
      </p>
      <div className="amigos-demo-grid">
        {AMIGOS_DEMO.map((a) => (
          <AmigoCard key={a.nombre} amigo={a} />
        ))}
      </div>
    </div>
  );
}
