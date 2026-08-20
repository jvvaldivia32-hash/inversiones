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
  // Generalizado para el simulador de "paper investing" (extra 2026-08-20): mismo
  // componente, mismo modelo de compra/venta por costo promedio ponderado, pero apunta a
  // otro endpoint. `permitirEditar=false` esconde "editar"/"cargar manual"/"borrar" — ahí
  // no hay un bróker externo con el que reconciliar, la app misma es la fuente de verdad,
  // así que esas acciones no tienen sentido (para cerrar una posición del todo, "vender
  // todo" ya cubre el caso).
  endpoint?: string;
  permitirEditar?: boolean;
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

type Accion = "guardar" | "comprar" | "vender" | "borrar";
type Modo = "idle" | "comprar" | "vender" | "editar" | "clave";

interface Payload {
  acciones: number;
  costo_base_usd: number;
}

interface Pendiente {
  accion: Accion;
  payload: Payload | null;
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
  endpoint = "/api/mi-inversion",
  permitirEditar = true,
}: Props) {
  const [modo, setModo] = useState<Modo>("idle");
  const [pendiente, setPendiente] = useState<Pendiente | null>(null);

  const [montoComprar, setMontoComprar] = useState("");
  const [montoVender, setMontoVender] = useState("");
  const [montoEditar, setMontoEditar] = useState("");
  const [pctMagnitud, setPctMagnitud] = useState("");
  const [pctNegativo, setPctNegativo] = useState(false);

  const [clave, setClave] = useState<string | null>(() => localStorage.getItem(CLAVE_STORAGE_KEY));
  const [claveInput, setClaveInput] = useState("");
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

  function abrirComprar() {
    setMontoComprar("");
    setErrorMsg(null);
    setModo("comprar");
  }

  function abrirVender() {
    setMontoVender("");
    setErrorMsg(null);
    setModo("vender");
  }

  // Al editar, se precargan el monto y % actuales *calculados en vivo* como punto de
  // partida — pero conviene que el usuario los reemplace por lo que diga su bróker hoy,
  // porque acá no hay forma de saber sobre compras/ventas que no haya cargado con los
  // botones de comprar/vender.
  function abrirEditar() {
    if (datos && precioActual > 0) {
      const { montoActual, gananciaPct } = calcularEnVivo(datos, precioActual);
      setMontoEditar(montoActual.toFixed(2));
      setPctNegativo(gananciaPct < 0);
      setPctMagnitud(Math.abs(gananciaPct).toFixed(2));
    } else {
      setMontoEditar("");
      setPctNegativo(false);
      setPctMagnitud("");
    }
    setErrorMsg(null);
    setModo("editar");
  }

  function calcularPayloadComprar(): { payload: Payload } | { errorMsg: string } {
    const monto = aNumero(montoComprar);
    if (!Number.isFinite(monto) || monto <= 0) {
      return { errorMsg: "el monto tiene que ser un número mayor a 0" };
    }
    if (!(precioActual > 0)) {
      return { errorMsg: "no hay precio actual todavía, intenta de nuevo en un rato" };
    }
    return { payload: { acciones: monto / precioActual, costo_base_usd: monto } };
  }

  function calcularPayloadVender(): { payload: Payload } | { errorMsg: string } {
    if (!datos) return { errorMsg: "no hay una posición guardada para vender" };
    const monto = aNumero(montoVender);
    if (!Number.isFinite(monto) || monto <= 0) {
      return { errorMsg: "el monto tiene que ser un número mayor a 0" };
    }
    if (!(precioActual > 0)) {
      return { errorMsg: "no hay precio actual todavía, intenta de nuevo en un rato" };
    }
    const { montoActual } = calcularEnVivo(datos, precioActual);
    if (monto > montoActual * 1.0001) {
      return { errorMsg: `no puedes vender más de lo que tienes (${formatUSD(montoActual)})` };
    }
    const accionesDelta = Math.min(monto / precioActual, datos.acciones);
    // Costo base retirado proporcional a la fracción de acciones vendida — método de
    // costo promedio, el mismo que ya usa "comprar" para promediar entre compras.
    const costoBaseDelta = datos.costo_base_usd * (accionesDelta / datos.acciones);
    return { payload: { acciones: accionesDelta, costo_base_usd: costoBaseDelta } };
  }

  function calcularPayloadEditar(): { payload: Payload } | { errorMsg: string } {
    const monto = aNumero(montoEditar);
    const pct = (pctNegativo ? -1 : 1) * aNumero(pctMagnitud);
    if (!Number.isFinite(monto) || monto <= 0) {
      return { errorMsg: "el monto tiene que ser un número mayor a 0" };
    }
    if (!Number.isFinite(pct) || pct <= -100) {
      return { errorMsg: "el % no puede ser -100 o menos" };
    }
    if (!(precioActual > 0)) {
      return { errorMsg: "no hay precio actual todavía, intenta de nuevo en un rato" };
    }
    return { payload: { acciones: monto / precioActual, costo_base_usd: monto / (1 + pct / 100) } };
  }

  async function enviar(claveAUsar: string, accion: Accion, payload: Payload | null) {
    setEnviando(true);
    setErrorMsg(null);
    try {
      const resp = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, accion, clave: claveAUsar, ...payload }),
      });

      if (resp.status === 401) {
        localStorage.removeItem(CLAVE_STORAGE_KEY);
        setClave(null);
        setPendiente({ accion, payload });
        setModo("clave");
        setErrorMsg("Clave incorrecta.");
        return;
      }
      if (!resp.ok) {
        const data = (await resp.json().catch(() => null)) as { error?: string } | null;
        setErrorMsg(data?.error ?? "No se pudo guardar. Intenta de nuevo.");
        return;
      }

      const data = (await resp.json()) as { datos: Record<string, MiInversionResumen> };
      localStorage.setItem(CLAVE_STORAGE_KEY, claveAUsar);
      setClave(claveAUsar);
      setClaveInput("");
      setPendiente(null);
      setModo("idle");
      onGuardado(ticker, data.datos[ticker] ?? null);
    } catch {
      setErrorMsg("No se pudo conectar. Intenta de nuevo.");
    } finally {
      setEnviando(false);
    }
  }

  function intentarEnviar(accion: Accion) {
    setErrorMsg(null);
    let payload: Payload | null = null;
    if (accion !== "borrar") {
      const resultado =
        accion === "comprar"
          ? calcularPayloadComprar()
          : accion === "vender"
            ? calcularPayloadVender()
            : calcularPayloadEditar();
      if ("errorMsg" in resultado) {
        setErrorMsg(resultado.errorMsg);
        return;
      }
      payload = resultado.payload;
    }
    if (clave) {
      enviar(clave, accion, payload);
    } else {
      setPendiente({ accion, payload });
      setModo("clave");
    }
  }

  function alConfirmarClave(e: FormEvent) {
    e.preventDefault();
    if (!claveInput || !pendiente) return;
    enviar(claveInput, pendiente.accion, pendiente.payload);
  }

  function cerrar() {
    setModo("idle");
    setErrorMsg(null);
  }

  if (modo === "clave") {
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
          <button type="button" onClick={cerrar} disabled={enviando}>
            cancelar
          </button>
        </div>
      </form>
    );
  }

  if (modo === "comprar") {
    return (
      <form
        className="mi-inversion-form"
        onSubmit={(e) => {
          e.preventDefault();
          intentarEnviar("comprar");
        }}
      >
        <label>
          ¿Cuánto compraste hoy? (USD)
          <input
            type="text"
            inputMode="decimal"
            value={montoComprar}
            onChange={(e) => setMontoComprar(e.target.value)}
            placeholder="10.00"
            autoFocus
            disabled={enviando}
          />
        </label>
        <p className="mi-inversion-nota">
          Se suma a lo que ya tenías, al precio de hoy ({formatUSD(precioActual)}).
        </p>
        {errorMsg && <p className="mi-inversion-error">{errorMsg}</p>}
        <div className="mi-inversion-botones">
          <button type="submit" disabled={enviando}>
            Comprar
          </button>
          <button type="button" onClick={cerrar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    );
  }

  if (modo === "vender") {
    return (
      <form
        className="mi-inversion-form"
        onSubmit={(e) => {
          e.preventDefault();
          intentarEnviar("vender");
        }}
      >
        <label>
          ¿Cuánto vendiste hoy? (USD, al valor de hoy)
          <input
            type="text"
            inputMode="decimal"
            value={montoVender}
            onChange={(e) => setMontoVender(e.target.value)}
            placeholder="10.00"
            autoFocus
            disabled={enviando}
          />
        </label>
        {datos && precioActual > 0 && (
          <button
            type="button"
            className="mi-inversion-vender-todo"
            onClick={() => setMontoVender(calcularEnVivo(datos, precioActual).montoActual.toFixed(2))}
            disabled={enviando}
          >
            vender todo ({formatUSD(calcularEnVivo(datos, precioActual).montoActual)})
          </button>
        )}
        {errorMsg && <p className="mi-inversion-error">{errorMsg}</p>}
        <div className="mi-inversion-botones">
          <button type="submit" disabled={enviando}>
            Vender
          </button>
          <button type="button" onClick={cerrar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    );
  }

  if (modo === "editar") {
    return (
      <form
        className="mi-inversion-form"
        onSubmit={(e) => {
          e.preventDefault();
          intentarEnviar("guardar");
        }}
      >
        <label>
          Monto actual (USD)
          <input
            type="text"
            inputMode="decimal"
            value={montoEditar}
            onChange={(e) => setMontoEditar(e.target.value)}
            placeholder="55.97"
            disabled={enviando}
          />
        </label>
        <label>
          % ganancia/pérdida (según tu bróker)
          <div className="mi-inversion-pct-row">
            <button
              type="button"
              className="mi-inversion-signo"
              onClick={() => setPctNegativo((v) => !v)}
              disabled={enviando}
              aria-label={pctNegativo ? "cambiar a ganancia" : "cambiar a pérdida"}
            >
              {pctNegativo ? "−" : "+"}
            </button>
            <input
              type="text"
              inputMode="decimal"
              value={pctMagnitud}
              onChange={(e) => setPctMagnitud(e.target.value)}
              placeholder="6.85"
              disabled={enviando}
            />
          </div>
        </label>
        <p className="mi-inversion-nota">
          Reemplaza todo lo guardado — úsalo si olvidaste cargar una compra/venta y prefieres
          poner directo lo que dice tu bróker.
        </p>
        {errorMsg && <p className="mi-inversion-error">{errorMsg}</p>}
        <div className="mi-inversion-botones">
          <button type="submit" disabled={enviando}>
            Guardar
          </button>
          <button type="button" onClick={cerrar} disabled={enviando}>
            Cancelar
          </button>
        </div>
      </form>
    );
  }

  if (!datos) {
    return (
      <div className="mi-inversion">
        <div className="mi-inversion-botones">
          <button type="button" onClick={abrirComprar}>
            + comprar
          </button>
          {permitirEditar && (
            <button type="button" onClick={abrirEditar}>
              cargar manual
            </button>
          )}
        </div>
        {errorMsg && <p className="mi-inversion-error">{errorMsg}</p>}
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
        <button type="button" onClick={abrirComprar} disabled={enviando}>
          + comprar
        </button>
        <button type="button" onClick={abrirVender} disabled={enviando}>
          − vender
        </button>
        {permitirEditar && (
          <>
            <button type="button" onClick={abrirEditar} disabled={enviando}>
              editar
            </button>
            <button type="button" onClick={() => intentarEnviar("borrar")} disabled={enviando}>
              borrar
            </button>
          </>
        )}
      </div>
      <p className="mi-inversion-nota">Sincronizado entre tus dispositivos, privado.</p>
    </div>
  );
}
