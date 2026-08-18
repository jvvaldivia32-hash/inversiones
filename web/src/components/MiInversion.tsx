import { useState, type FormEvent } from "react";
import { formatUSD, formatNumeroCL } from "../lib/format";
import "./MiInversion.css";

// Misma clave que PanelWatchlist.tsx (WATCHLIST_EDIT_KEY del lado del servidor) — se
// reutiliza el mismo candado y el mismo localStorage para no pedirle la clave dos veces
// si ya la tipeó para editar la watchlist.
const CLAVE_STORAGE_KEY = "inversiones_watchlist_clave";

export interface MiInversionResumen {
  monto: number;
  pct: number;
}

interface Props {
  ticker: string;
  precioActual: number;
  datos: MiInversionResumen | null;
  cargando: boolean;
  error: boolean;
  onGuardado: (ticker: string, datos: MiInversionResumen | null) => void;
}

function aNumero(texto: string): number {
  return Number(texto.trim().replace(",", "."));
}

export default function MiInversion({
  ticker,
  precioActual,
  datos,
  cargando,
  error,
  onGuardado,
}: Props) {
  const [editando, setEditando] = useState(false);
  const [monto, setMonto] = useState("");
  const [pct, setPct] = useState("");
  const [clave, setClave] = useState<string | null>(() => localStorage.getItem(CLAVE_STORAGE_KEY));
  const [claveInput, setClaveInput] = useState("");
  const [pidiendoClave, setPidiendoClave] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (error) {
    return (
      <p className="mi-inversion-error">
        No se pudo cargar "mi inversión" ahora. Los demás datos siguen disponibles.
      </p>
    );
  }

  if (cargando) {
    return <p className="mi-inversion-nota">cargando…</p>;
  }

  function abrirForm() {
    setMonto(datos ? String(datos.monto) : "");
    setPct(datos ? String(datos.pct) : "");
    setErrorMsg(null);
    setEditando(true);
  }

  async function enviar(claveAUsar: string, accion: "guardar" | "borrar") {
    setEnviando(true);
    setErrorMsg(null);
    try {
      const m = accion === "guardar" ? aNumero(monto) : undefined;
      const p = accion === "guardar" ? aNumero(pct) : undefined;
      if (accion === "guardar") {
        if (!Number.isFinite(m) || (m as number) <= 0) {
          setErrorMsg("el monto tiene que ser un número mayor a 0");
          setEnviando(false);
          return;
        }
        if (!Number.isFinite(p) || (p as number) <= -100) {
          setErrorMsg("el % no puede ser -100 o menos");
          setEnviando(false);
          return;
        }
      }

      const resp = await fetch("/api/mi-inversion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, accion, clave: claveAUsar, monto: m, pct: p }),
      });

      if (resp.status === 401) {
        localStorage.removeItem(CLAVE_STORAGE_KEY);
        setClave(null);
        setPidiendoClave(true);
        setErrorMsg("Clave incorrecta.");
        return;
      }
      if (!resp.ok) {
        setErrorMsg("No se pudo guardar. Intenta de nuevo.");
        return;
      }

      localStorage.setItem(CLAVE_STORAGE_KEY, claveAUsar);
      setClave(claveAUsar);
      setClaveInput("");
      setPidiendoClave(false);
      setEditando(false);
      onGuardado(ticker, accion === "guardar" ? { monto: m as number, pct: p as number } : null);
    } catch {
      setErrorMsg("No se pudo conectar. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  }

  function alGuardar(e: FormEvent) {
    e.preventDefault();
    if (clave) {
      enviar(clave, "guardar");
    } else {
      setPidiendoClave(true);
    }
  }

  function alBorrar() {
    if (clave) {
      enviar(clave, "borrar");
    } else {
      setPidiendoClave(true);
    }
  }

  function alConfirmarClave(e: FormEvent) {
    e.preventDefault();
    if (!claveInput) return;
    enviar(claveInput, editando ? "guardar" : "borrar");
  }

  if (pidiendoClave) {
    return (
      <form className="mi-inversion-form" onSubmit={alConfirmarClave}>
        <label>
          Clave
          <input
            type="password"
            value={claveInput}
            onChange={(e) => setClaveInput(e.target.value)}
            autoFocus
            disabled={enviando}
          />
        </label>
        {errorMsg && <p className="mi-inversion-error">{errorMsg}</p>}
        <div className="mi-inversion-botones">
          <button type="submit" disabled={enviando || !claveInput}>
            confirmar
          </button>
          <button type="button" onClick={() => setPidiendoClave(false)} disabled={enviando}>
            cancelar
          </button>
        </div>
      </form>
    );
  }

  if (editando) {
    return (
      <form className="mi-inversion-form" onSubmit={alGuardar}>
        <label>
          Monto actual (USD)
          <input
            type="text"
            inputMode="decimal"
            value={monto}
            onChange={(e) => setMonto(e.target.value)}
            placeholder="55.97"
            disabled={enviando}
          />
        </label>
        <label>
          % ganancia/pérdida (según tu bróker)
          <input
            type="text"
            inputMode="decimal"
            value={pct}
            onChange={(e) => setPct(e.target.value)}
            placeholder="6.85"
            disabled={enviando}
          />
        </label>
        {errorMsg && <p className="mi-inversion-error">{errorMsg}</p>}
        <div className="mi-inversion-botones">
          <button type="submit" disabled={enviando}>
            Guardar
          </button>
          <button type="button" onClick={() => setEditando(false)} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    );
  }

  if (!datos) {
    return (
      <div className="mi-inversion">
        <button type="button" onClick={abrirForm}>
          + agregar mi inversión
        </button>
        <p className="mi-inversion-nota">Sincronizado entre tus dispositivos, privado.</p>
      </div>
    );
  }

  const acciones = precioActual > 0 ? datos.monto / precioActual : 0;
  const costoBase = datos.monto / (1 + datos.pct / 100);
  const gananciaUsd = datos.monto - costoBase;
  const claseGanancia = gananciaUsd >= 0 ? "var-positiva" : "var-negativa";

  return (
    <div className="mi-inversion">
      <ul className="mi-inversion-detalle">
        <li>
          <span>Acciones</span>
          <strong>{formatNumeroCL(acciones, 6)}</strong>
        </li>
        <li>
          <span>Costo base</span>
          <strong>{formatUSD(costoBase)}</strong>
        </li>
        <li className={claseGanancia}>
          <span>Ganancia</span>
          <strong>
            {gananciaUsd >= 0 ? "+" : ""}
            {formatUSD(gananciaUsd)}
          </strong>
        </li>
      </ul>
      {errorMsg && <p className="mi-inversion-error">{errorMsg}</p>}
      <div className="mi-inversion-botones">
        <button type="button" onClick={abrirForm} disabled={enviando}>
          editar
        </button>
        <button type="button" onClick={alBorrar} disabled={enviando}>
          borrar
        </button>
      </div>
      <p className="mi-inversion-nota">Sincronizado entre tus dispositivos, privado.</p>
    </div>
  );
}
