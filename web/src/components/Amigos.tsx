import { useState, type FormEvent } from "react";
import type { Amigo, AmigoTickerDato } from "../types";
import { formatPct, formatUSD } from "../lib/format";
import "./Amigos.css";

/**
 * Sección "Amigos" — extra fuera del plan madre (2026-08-14). Cada amigo elige tickers
 * propios o una palabra clave (mini recap de noticias), y edita lo suyo desde su propio
 * link (?amigo=<id>) sin ninguna clave compartida: el límite real contra abuso vive en
 * web/api/amigos.ts, que nunca deja crear un id nuevo, solo editar uno que ya existe.
 * Los datos reales (precio, titulares) los resuelve collector/amigos_diario.py una vez
 * al día — esto acá solo lee lo que ya quedó en daily.json y, si corresponde, muestra el
 * formulario de edición.
 */

function idAmigoDesdeUrl(): string | null {
  return new URLSearchParams(window.location.search).get("amigo");
}

function MiniTicker({ t }: { t: AmigoTickerDato }) {
  const clase = t.var_dia_pct >= 0 ? "var-positiva" : "var-negativa";
  return (
    <div className="amigos-ticker">
      <span className="amigos-ticker-simbolo">{t.ticker}</span>
      <span>{formatUSD(t.precio)}</span>
      <span className={clase}>{formatPct(t.var_dia_pct)}</span>
    </div>
  );
}

function AmigoCard({ amigo }: { amigo: Amigo }) {
  const tickers = amigo.datos.tickers ?? [];
  const titulares = amigo.datos.titulares ?? [];

  return (
    <div className="amigos-card">
      <h5>{amigo.nombre}</h5>
      {amigo.modo === "tickers" ? (
        tickers.length > 0 ? (
          tickers.map((t) => <MiniTicker key={t.ticker} t={t} />)
        ) : (
          <p className="amigos-vacio">sin datos todavía</p>
        )
      ) : (
        <>
          <p className="amigos-modo">"{amigo.datos.palabra_clave}"</p>
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
        </>
      )}
    </div>
  );
}

function PanelEdicion({ id, amigoActual }: { id: string; amigoActual?: Amigo }) {
  const [modo, setModo] = useState<"tickers" | "palabra_clave">(amigoActual?.modo ?? "tickers");
  const [tickersTexto, setTickersTexto] = useState(
    (amigoActual?.datos.tickers ?? []).map((t) => t.ticker).join(", "),
  );
  const [palabraClave, setPalabraClave] = useState(amigoActual?.datos.palabra_clave ?? "");
  const [estado, setEstado] = useState<"idle" | "enviando" | "ok" | "error">("idle");
  const [error, setError] = useState("");

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEstado("enviando");
    setError("");

    const body: Record<string, unknown> = { id, modo };
    if (modo === "tickers") {
      body.tickers = tickersTexto
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
    } else {
      body.palabra_clave = palabraClave.trim();
    }

    try {
      const resp = await fetch("/api/amigos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
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
        Editando {amigoActual ? amigoActual.nombre : "tu tarjeta"} — el cambio aparece en
        el recap de mañana, no altera nada de "Mis inversiones".
      </p>
      <div className="amigos-panel-modo" role="group" aria-label="Modo">
        <button
          type="button"
          className={modo === "tickers" ? "activo" : ""}
          onClick={() => setModo("tickers")}
        >
          Tickers
        </button>
        <button
          type="button"
          className={modo === "palabra_clave" ? "activo" : ""}
          onClick={() => setModo("palabra_clave")}
        >
          Palabra clave
        </button>
      </div>
      {modo === "tickers" ? (
        <input
          type="text"
          placeholder="ej: NVDA, TSLA (máx. 2)"
          value={tickersTexto}
          onChange={(e) => setTickersTexto(e.target.value)}
        />
      ) : (
        <input
          type="text"
          placeholder="ej: baterías de litio"
          maxLength={40}
          value={palabraClave}
          onChange={(e) => setPalabraClave(e.target.value)}
        />
      )}
      <button type="submit" disabled={estado === "enviando"}>
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
