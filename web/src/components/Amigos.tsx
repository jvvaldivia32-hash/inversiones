import { useState, type FormEvent } from "react";
import type { Amigo, AmigoSeguimiento } from "../types";
import { formatPct, formatUSD } from "../lib/format";
import "./Amigos.css";

/**
 * Sección "Amigos" — extra fuera del plan madre (2026-08-14). Cada amigo arma su propia
 * mini lista de seguimientos (mezcla libre de tickers propios y palabras clave, hasta 4
 * en total, máx. 2 tickers) y la edita desde su propio link (?amigo=<id>) sin ninguna
 * clave compartida: el límite real contra abuso vive en web/api/amigos.ts, que nunca deja
 * crear un id nuevo, solo editar uno que ya existe. Los datos reales (precio, titulares)
 * los resuelve collector/amigos_diario.py una vez al día.
 */

const MAX_SEGUIMIENTOS = 4;
const MAX_TICKERS = 2;

function idAmigoDesdeUrl(): string | null {
  return new URLSearchParams(window.location.search).get("amigo");
}

function FilaSeguimiento({ s }: { s: AmigoSeguimiento }) {
  if (s.tipo === "ticker") {
    if (!s.datos || s.datos.precio === undefined) {
      return (
        <div className="amigos-ticker">
          <span className="amigos-ticker-simbolo">{s.valor}</span>
          <span className="amigos-vacio">sin datos todavía</span>
        </div>
      );
    }
    const clase = (s.datos.var_dia_pct ?? 0) >= 0 ? "var-positiva" : "var-negativa";
    return (
      <div className="amigos-ticker">
        <span className="amigos-ticker-simbolo">{s.valor}</span>
        <span>{formatUSD(s.datos.precio)}</span>
        <span className={clase}>{formatPct(s.datos.var_dia_pct ?? 0)}</span>
      </div>
    );
  }

  const titulares = s.datos?.titulares ?? [];
  return (
    <div className="amigos-tema">
      <p className="amigos-modo">"{s.valor}"</p>
      {titulares.length > 0 ? (
        <ul className="amigos-titulares">
          {titulares.map((n) => (
            <li key={n.url}>
              <a href={n.url} target="_blank" rel="noreferrer">
                {n.titular}
              </a>{" "}
              <span className="amigos-medio">[{n.medio}]</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="amigos-vacio">sin titulares todavía</p>
      )}
    </div>
  );
}

function AmigoCard({ amigo }: { amigo: Amigo }) {
  return (
    <div className="amigos-card">
      <h5>{amigo.nombre}</h5>
      {amigo.seguimientos.length > 0 ? (
        amigo.seguimientos.map((s, i) => <FilaSeguimiento key={`${s.tipo}-${s.valor}-${i}`} s={s} />)
      ) : (
        <p className="amigos-vacio">sin seguimientos todavía</p>
      )}
    </div>
  );
}

function PanelEdicion({ id, amigoActual }: { id: string; amigoActual?: Amigo }) {
  const [nombre, setNombre] = useState(amigoActual?.nombre ?? "");
  const [seguimientos, setSeguimientos] = useState<{ tipo: "ticker" | "palabra_clave"; valor: string }[]>(
    (amigoActual?.seguimientos ?? []).map((s) => ({ tipo: s.tipo, valor: s.valor })),
  );
  const [nuevoTipo, setNuevoTipo] = useState<"ticker" | "palabra_clave">("ticker");
  const [nuevoValor, setNuevoValor] = useState("");
  const [estado, setEstado] = useState<"idle" | "enviando" | "ok" | "error">("idle");
  const [error, setError] = useState("");

  const cantidadTickers = seguimientos.filter((s) => s.tipo === "ticker").length;
  const lleno = seguimientos.length >= MAX_SEGUIMIENTOS;
  const tickersLlenos = cantidadTickers >= MAX_TICKERS;

  function agregar() {
    const valor = nuevoValor.trim();
    if (!valor || lleno) return;
    if (nuevoTipo === "ticker" && tickersLlenos) return;
    setSeguimientos((actuales) => [...actuales, { tipo: nuevoTipo, valor }]);
    setNuevoValor("");
  }

  function quitar(indice: number) {
    setSeguimientos((actuales) => actuales.filter((_, i) => i !== indice));
  }

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (seguimientos.length === 0) {
      setError("agrega al menos un ticker o palabra clave");
      setEstado("error");
      return;
    }
    setEstado("enviando");
    setError("");

    try {
      const resp = await fetch("/api/amigos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, nombre: nombre.trim() || undefined, seguimientos }),
      });
      const data = (await resp.json()) as { error?: string };
      if (!resp.ok) {
        setError(data.error ?? "no se pudo actualizar");
        setEstado("error");
        return;
      }
      setEstado("ok");
    } catch {
      setError("no se pudo conectar con el servidor");
      setEstado("error");
    }
  }

  return (
    <form className="amigos-panel-edicion" onSubmit={enviar}>
      <p className="amigos-panel-titulo">
        Tu mini dashboard — mezcla hasta {MAX_SEGUIMIENTOS} tickers y temas (máx.{" "}
        {MAX_TICKERS} tickers). El cambio aparece en el recap de mañana, no altera nada de
        "Mis inversiones".
      </p>

      <input
        type="text"
        placeholder="Tu nombre"
        maxLength={20}
        value={nombre}
        onChange={(e) => setNombre(e.target.value)}
      />

      <ul className="amigos-panel-lista">
        {seguimientos.map((s, i) => (
          <li key={`${s.tipo}-${s.valor}-${i}`}>
            <span className="amigos-panel-lista-tipo">{s.tipo === "ticker" ? "$" : "#"}</span>
            {s.valor}
            <button type="button" onClick={() => quitar(i)} aria-label={`quitar ${s.valor}`}>
              ×
            </button>
          </li>
        ))}
      </ul>

      {!lleno && (
        <div className="amigos-panel-agregar">
          <div className="amigos-panel-modo" role="group" aria-label="Tipo">
            <button
              type="button"
              className={nuevoTipo === "ticker" ? "activo" : ""}
              onClick={() => setNuevoTipo("ticker")}
              disabled={tickersLlenos}
            >
              Ticker
            </button>
            <button
              type="button"
              className={nuevoTipo === "palabra_clave" ? "activo" : ""}
              onClick={() => setNuevoTipo("palabra_clave")}
            >
              Palabra clave
            </button>
          </div>
          <div className="amigos-panel-agregar-fila">
            <input
              type="text"
              placeholder={nuevoTipo === "ticker" ? "ej: NVDA" : "ej: baterías de litio"}
              maxLength={nuevoTipo === "ticker" ? 10 : 40}
              value={nuevoValor}
              onChange={(e) => setNuevoValor(e.target.value)}
            />
            <button type="button" onClick={agregar} disabled={!nuevoValor.trim()}>
              agregar
            </button>
          </div>
        </div>
      )}

      <button type="submit" className="amigos-panel-guardar" disabled={estado === "enviando"}>
        {estado === "enviando" ? "guardando..." : "guardar"}
      </button>
      {estado === "ok" && <p className="amigos-panel-ok">Listo, quedó guardado.</p>}
      {estado === "error" && <p className="amigos-panel-error">{error}</p>}
    </form>
  );
}

export default function Amigos({ amigos }: { amigos: Amigo[] }) {
  const idDeUrl = idAmigoDesdeUrl();
  const amigoActual = idDeUrl ? amigos.find((a) => a.id === idDeUrl) : undefined;

  return (
    <div className="amigos">
      {idDeUrl && <PanelEdicion id={idDeUrl} amigoActual={amigoActual} />}

      {amigos.length > 0 ? (
        <div className="amigos-grid">
          {amigos.map((a) => (
            <AmigoCard key={a.id} amigo={a} />
          ))}
        </div>
      ) : (
        <p className="amigos-vacio">Todavía no hay amigos agregados.</p>
      )}
    </div>
  );
}
