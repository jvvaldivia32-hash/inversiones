import { useState } from "react";
import type { FormEvent } from "react";
import "./PanelWatchlist.css";

const CLAVE_STORAGE_KEY = "inversiones_watchlist_clave";

type Accion = "agregar" | "quitar";

interface PanelWatchlistProps {
  watchlist: string[] | null;
  error: boolean;
  onChange: (tickers: string[]) => void;
}

export default function PanelWatchlist({ watchlist, error, onChange }: PanelWatchlistProps) {
  const [expandida, setExpandida] = useState(false);
  const [nuevoTicker, setNuevoTicker] = useState("");
  const [clave, setClave] = useState<string | null>(() =>
    localStorage.getItem(CLAVE_STORAGE_KEY),
  );
  const [claveInput, setClaveInput] = useState("");
  const [accionPendiente, setAccionPendiente] = useState<{ ticker: string; accion: Accion } | null>(
    null,
  );
  const [cargando, setCargando] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (error) {
    return (
      <p className="panel-watchlist-error">
        No se pudo cargar la watchlist en vivo. Los datos de hoy siguen disponibles, pero
        agregar o quitar tickers no está disponible ahora.
      </p>
    );
  }

  if (watchlist === null) return null;

  async function enviar(ticker: string, accion: Accion, claveAUsar: string) {
    setCargando(true);
    setErrorMsg(null);
    try {
      const resp = await fetch("/api/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, accion, clave: claveAUsar }),
      });

      if (resp.status === 401) {
        localStorage.removeItem(CLAVE_STORAGE_KEY);
        setClave(null);
        setErrorMsg("Clave incorrecta.");
        setAccionPendiente({ ticker, accion });
        return;
      }
      if (!resp.ok) {
        setErrorMsg("No se pudo actualizar la watchlist. Intenta de nuevo.");
        return;
      }

      const data = (await resp.json()) as { tickers: string[] };
      localStorage.setItem(CLAVE_STORAGE_KEY, claveAUsar);
      setClave(claveAUsar);
      setAccionPendiente(null);
      setClaveInput("");
      setNuevoTicker("");
      onChange(data.tickers);
    } catch {
      setErrorMsg("No se pudo conectar. Intenta de nuevo.");
    } finally {
      setCargando(false);
    }
  }

  function solicitar(tickerCrudo: string, accion: Accion) {
    const ticker = tickerCrudo.trim().toUpperCase();
    if (!ticker) return;
    setErrorMsg(null);
    if (clave) {
      enviar(ticker, accion, clave);
    } else {
      setAccionPendiente({ ticker, accion });
    }
  }

  function alAgregar(e: FormEvent) {
    e.preventDefault();
    solicitar(nuevoTicker, "agregar");
  }

  function alConfirmarClave(e: FormEvent) {
    e.preventDefault();
    if (!accionPendiente || !claveInput) return;
    enviar(accionPendiente.ticker, accionPendiente.accion, claveInput);
  }

  return (
    <div className="panel-watchlist">
      <button
        type="button"
        className="panel-watchlist-toggle"
        onClick={() => setExpandida((v) => !v)}
        aria-expanded={expandida}
      >
        {expandida ? "cerrar watchlist ▴" : "editar watchlist ▾"}
      </button>

      {expandida && (
        <div className="panel-watchlist-cuerpo">
          <ul className="panel-watchlist-lista">
            {watchlist.map((t) => (
              <li key={t}>
                <span>{t}</span>
                <button
                  type="button"
                  disabled={cargando}
                  onClick={() => solicitar(t, "quitar")}
                  aria-label={`Quitar ${t} de la watchlist`}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>

          <form className="panel-watchlist-form" onSubmit={alAgregar}>
            <input
              type="text"
              value={nuevoTicker}
              onChange={(e) => setNuevoTicker(e.target.value)}
              placeholder="Ticker nuevo (ej. AAPL)"
              disabled={cargando}
            />
            <button type="submit" disabled={cargando || !nuevoTicker.trim()}>
              agregar
            </button>
          </form>

          {accionPendiente && (
            <form className="panel-watchlist-clave" onSubmit={alConfirmarClave}>
              <label>
                Clave para {accionPendiente.accion === "agregar" ? "agregar" : "quitar"}{" "}
                {accionPendiente.ticker}
                <input
                  type="password"
                  value={claveInput}
                  onChange={(e) => setClaveInput(e.target.value)}
                  autoFocus
                  disabled={cargando}
                />
              </label>
              <button type="submit" disabled={cargando || !claveInput}>
                confirmar
              </button>
            </form>
          )}

          {errorMsg && <p className="panel-watchlist-error">{errorMsg}</p>}
        </div>
      )}
    </div>
  );
}
