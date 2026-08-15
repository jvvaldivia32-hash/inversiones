import { useState, type FormEvent } from "react";
import type { Amigo, AmigoSeguimiento } from "../types";
import { formatPct, formatUSD } from "../lib/format";
import "./Amigos.css";

/**
 * Sección "Otros" (nav) / "Amigos" internamente — extra fuera del plan madre
 * (2026-08-14, gate de contraseña agregado 2026-08-15). Cada amigo arma su propia mini
 * lista de seguimientos (mezcla libre de tickers propios y palabras clave, hasta 4 en
 * total, máx. 2 tickers).
 *
 * Antes se editaba entrando con un link mágico (?amigo=<id>) — sin ese link la sección
 * era de solo lectura y no había ningún indicio de que existiera un modo edición, cosa
 * que confundió al propio José probándola. Ahora hay dos capas, ninguna es autenticación
 * real (todo esto sigue siendo público en el repo, a propósito — ver web/api/amigos.ts
 * para el límite real contra abuso):
 *   1. Una clave general para entrar a "Otros" (CLAVE_ENTRADA, hardcodeada a propósito).
 *   2. Adentro, elegís tu nombre y esa persona tiene su propia clave (campo `clave` en
 *      data/amigos.json) — así Amigo 1 y Amigo 2 no se confunden editando la tarjeta
 *      del otro por error.
 */

const MAX_SEGUIMIENTOS = 4;
const MAX_TICKERS = 2;
const CLAVE_ENTRADA = "amigos";
const STORAGE_KEY = "inversiones_otros_amigo_id";
const STORAGE_KEY_ENTRADA = "inversiones_otros_entrada_ok";

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

function GateEntrada({ onOk }: { onOk: () => void }) {
  const [claveInput, setClaveInput] = useState("");
  const [error, setError] = useState(false);

  function enviar(e: FormEvent) {
    e.preventDefault();
    if (claveInput.trim().toLowerCase() !== CLAVE_ENTRADA) {
      setError(true);
      return;
    }
    localStorage.setItem(STORAGE_KEY_ENTRADA, "1");
    onOk();
  }

  return (
    <form className="amigos-gate" onSubmit={enviar}>
      <p className="amigos-gate-titulo">Esta parte es privada — ingresa la contraseña.</p>
      <div className="amigos-gate-fila">
        <input
          type="password"
          placeholder="contraseña"
          value={claveInput}
          onChange={(e) => {
            setClaveInput(e.target.value);
            setError(false);
          }}
          autoFocus
        />
        <button type="submit" disabled={!claveInput.trim()}>
          entrar
        </button>
      </div>
      {error && <p className="amigos-panel-error">contraseña incorrecta</p>}
    </form>
  );
}

function Selector({ amigos, onElegir }: { amigos: Amigo[]; onElegir: (a: Amigo) => void }) {
  return (
    <div className="amigos-selector">
      <p className="amigos-gate-titulo">Esta parte es privada — ¿quién eres?</p>
      <div className="amigos-selector-botones">
        {amigos.map((a) => (
          <button key={a.id} type="button" onClick={() => onElegir(a)}>
            {a.nombre}
          </button>
        ))}
      </div>
    </div>
  );
}

function GateClave({
  amigo,
  onEntrar,
  onVolver,
}: {
  amigo: Amigo;
  onEntrar: (id: string) => void;
  onVolver: () => void;
}) {
  const [claveInput, setClaveInput] = useState("");
  const [error, setError] = useState(false);

  function enviar(e: FormEvent) {
    e.preventDefault();
    const ok = amigo.clave && amigo.clave.trim().toLowerCase() === claveInput.trim().toLowerCase();
    if (!ok) {
      setError(true);
      return;
    }
    localStorage.setItem(STORAGE_KEY, amigo.id);
    onEntrar(amigo.id);
  }

  return (
    <form className="amigos-gate" onSubmit={enviar}>
      <button type="button" className="amigos-salir" onClick={onVolver}>
        ← volver
      </button>
      <p className="amigos-gate-titulo">Contraseña de {amigo.nombre}</p>
      <div className="amigos-gate-fila">
        <input
          type="password"
          placeholder="contraseña"
          value={claveInput}
          onChange={(e) => {
            setClaveInput(e.target.value);
            setError(false);
          }}
          autoFocus
        />
        <button type="submit" disabled={!claveInput.trim()}>
          entrar
        </button>
      </div>
      {error && <p className="amigos-panel-error">contraseña incorrecta</p>}
    </form>
  );
}

function PaginaAmigo({ amigo, onSalir }: { amigo: Amigo; onSalir: () => void }) {
  return (
    <div className="amigos-pagina">
      <button type="button" className="amigos-salir" onClick={onSalir}>
        ← salir
      </button>
      <PanelEdicion id={amigo.id} amigoActual={amigo} />
      <AmigoCard amigo={amigo} />
    </div>
  );
}

export default function Amigos({ amigos }: { amigos: Amigo[] }) {
  const [entradaOk, setEntradaOk] = useState(() => localStorage.getItem(STORAGE_KEY_ENTRADA) === "1");
  const [idAutenticado, setIdAutenticado] = useState<string | null>(() =>
    localStorage.getItem(STORAGE_KEY),
  );
  const [amigoElegido, setAmigoElegido] = useState<Amigo | null>(null);

  const amigoActual = idAutenticado ? amigos.find((a) => a.id === idAutenticado) : undefined;

  function salir() {
    localStorage.removeItem(STORAGE_KEY);
    setIdAutenticado(null);
    setAmigoElegido(null);
  }

  if (amigoActual) {
    return (
      <div className="amigos">
        <PaginaAmigo amigo={amigoActual} onSalir={salir} />
      </div>
    );
  }

  if (!entradaOk) {
    return (
      <div className="amigos">
        <GateEntrada onOk={() => setEntradaOk(true)} />
      </div>
    );
  }

  if (amigos.length === 0) {
    return (
      <div className="amigos">
        <p className="amigos-vacio">Todavía no hay nadie agregado.</p>
      </div>
    );
  }

  if (amigoElegido) {
    return (
      <div className="amigos">
        <GateClave amigo={amigoElegido} onEntrar={setIdAutenticado} onVolver={() => setAmigoElegido(null)} />
      </div>
    );
  }

  return (
    <div className="amigos">
      <Selector amigos={amigos} onElegir={setAmigoElegido} />
    </div>
  );
}
