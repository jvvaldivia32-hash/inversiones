import { useState, type FormEvent } from "react";
import { formatUSD, formatPct, formatNumeroCL } from "../lib/format";
import "./MiInversion.css";

// Misma clave que PanelWatchlist.tsx (WATCHLIST_EDIT_KEY del lado del servidor) — se
// reutiliza el mismo candado y el mismo localStorage para no pedirle la clave dos veces
// si ya la tipeó para editar la watchlist.
const CLAVE_STORAGE_KEY = "inversiones_watchlist_clave";

// Lo único que se guarda es lo que NO cambia con el precio: cuántas acciones tiene y
// cuánto costaron en total. El monto actual y el % de ganancia se recalculan en cada
// render contra el precio de hoy — si se guardara el monto/% tal cual los tipeó el
// usuario, quedarían congelados para siempre y nunca se moverían con la acción (bug real
// de la primera versión, visto en vivo: José entró 55.97/+6.85% en VOO y una hora después
// seguía mostrando exactamente lo mismo pese a que el precio ya había cambiado).
export interface MiInversionResumen {
  acciones: number;
  costo_base_usd: number;
}

interface Props {
  ticker: string;
  precioActual: number;
  datos: MiInversionResumen | null;
  cargando: boolean;
  error: boolean;
  onGuardado: (ticker: string, datos: MiInversionResumen | null) => void;
}

// Única fuente de verdad para pasar de (acciones, costo base) fijos a (valor actual,
// ganancia) en vivo — la usan tanto el detalle de acá abajo como el resumen del header en
// CardInversion.tsx, para que nunca se desincronicen.
export function calcularEnVivo(datos: MiInversionResumen, precioActual: number) {
  const montoActual = datos.acciones * precioActual;
  const gananciaUsd = montoActual - datos.costo_base_usd;
  const gananciaPct = (gananciaUsd / datos.costo_base_usd) * 100;
  return { montoActual, gananciaUsd, gananciaPct };
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

  // Al editar, se precargan el monto y % actuales *calculados en vivo* como punto de
  // partida — pero conviene que el usuario los reemplace por lo que diga su bróker hoy,
  // porque acá no hay forma de saber sobre compras nuevas, dividendos reinvertidos, etc.
  function abrirForm() {
    if (datos && precioActual > 0) {
      const { montoActual, gananciaPct } = calcularEnVivo(datos, precioActual);
      setMonto(montoActual.toFixed(2));
      setPct(gananciaPct.toFixed(2));
    } else {
      setMonto("");
      setPct("");
    }
    setErrorMsg(null);
    setEditando(true);
  }

  async function enviar(claveAUsar: string, accion: "guardar" | "borrar") {
    setEnviando(true);
    setErrorMsg(null);
    try {
      let acciones: number | undefined;
      let costoBaseUsd: number | undefined;

      if (accion === "guardar") {
        const m = aNumero(monto);
        const p = aNumero(pct);
        if (!Number.isFinite(m) || m <= 0) {
          setErrorMsg("el monto tiene que ser un número mayor a 0");
          setEnviando(false);
          return;
        }
        if (!Number.isFinite(p) || p <= -100) {
          setErrorMsg("el % no puede ser -100 o menos");
          setEnviando(false);
          return;
        }
        if (!(precioActual > 0)) {
          setErrorMsg("no hay precio actual todavía, intenta de nuevo en un rato");
          setEnviando(false);
          return;
        }
        acciones = m / precioActual;
        costoBaseUsd = m / (1 + p / 100);
      }

      const resp = await fetch("/api/mi-inversion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker,
          accion,
          clave: claveAUsar,
          acciones,
          costo_base_usd: costoBaseUsd,
        }),
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
      onGuardado(
        ticker,
        accion === "guardar" ? { acciones: acciones as number, costo_base_usd: costoBaseUsd as number } : null,
      );
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

  const { montoActual, gananciaUsd, gananciaPct } = calcularEnVivo(datos, precioActual);
  const claseGanancia = gananciaUsd >= 0 ? "var-positiva" : "var-negativa";

  return (
    <div className="mi-inversion">
      <ul className="mi-inversion-detalle">
        <li>
          <span>Acciones</span>
          <strong>{formatNumeroCL(datos.acciones, 6)}</strong>
        </li>
        <li>
          <span>Valor actual</span>
          <strong>{formatUSD(montoActual)}</strong>
        </li>
        <li>
          <span>Costo base</span>
          <strong>{formatUSD(datos.costo_base_usd)}</strong>
        </li>
        <li className={claseGanancia}>
          <span>Ganancia</span>
          <strong>
            {gananciaUsd >= 0 ? "+" : ""}
            {formatUSD(gananciaUsd)} ({formatPct(gananciaPct)})
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
