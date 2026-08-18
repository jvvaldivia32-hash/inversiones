import type { IncomingMessage, ServerResponse } from "node:http";

// Mismo patrón de escritura que web/api/watchlist.ts y web/api/tesis.ts, pero apunta a
// un repo DISTINTO y privado (jvvaldivia32-hash/inversiones-privado) — a diferencia de la
// watchlist o las tesis, este archivo guarda montos reales en USD que el usuario invirtió,
// y el repo principal es público. Token separado (GITHUB_WRITE_TOKEN_PRIVADO, PAT de
// permiso mínimo acotado solo a ese repo) para no ampliarle el alcance al token que ya
// escribe en el repo público. La clave de edición sí se reutiliza (WATCHLIST_EDIT_KEY) —
// mismo candado mínimo de "app de un solo usuario" que ya existe para watchlist/tesis.
interface VercelRequest extends IncomingMessage {
  method?: string;
  body?: unknown;
}

interface VercelResponse extends ServerResponse {
  status(code: number): VercelResponse;
  json(body: unknown): VercelResponse;
}

const OWNER = "jvvaldivia32-hash";
const REPO = "inversiones-privado";
const RUTA_ARCHIVO = "mi-inversion.json";
const RAMA = "main";
const USER_AGENT = "inversiones-mi-inversion-panel";
const TICKER_VALIDO = /^[A-Z0-9.]{1,10}$/;

// Se guarda lo que NO cambia con el precio (acciones y costo base), no el monto/% del
// bróker tal cual — esos se recalculan en el visor contra el precio de cada momento
// (ver calcularEnVivo en web/src/components/MiInversion.tsx). Guardar el monto/% crudo
// los deja congelados para siempre, que fue el bug real de la primera versión.
interface Posicion {
  acciones: number;
  costo_base_usd: number;
}

type Datos = Record<string, Posicion>;
type Accion = "guardar" | "comprar" | "vender" | "borrar";

// Distingue un rechazo de negocio (ticker sin posición, venta mayor a lo que hay) de una
// falla real de GitHub — el handler los traduce a 400 vs 502.
class ErrorValidacion extends Error {}

// Tolerancia para "vendí todo": floats nunca calzan exacto entre lo que computó el
// navegador y lo que hay guardado.
const EPSILON = 1e-6;

interface ArchivoGitHub {
  sha: string;
  datos: Datos;
}

async function leerArchivo(token: string): Promise<ArchivoGitHub> {
  const resp = await fetch(
    `https://api.github.com/repos/${OWNER}/${REPO}/contents/${RUTA_ARCHIVO}?ref=${RAMA}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        "User-Agent": USER_AGENT,
        Accept: "application/vnd.github+json",
      },
    },
  );
  if (!resp.ok) {
    throw new Error(`GitHub GET ${resp.status}`);
  }
  const data = (await resp.json()) as { sha: string; content: string };
  const contenido = Buffer.from(data.content, "base64").toString("utf8");
  const datos = JSON.parse(contenido || "{}") as Datos;
  return { sha: data.sha, datos };
}

async function escribirArchivo(
  token: string,
  sha: string,
  datos: Datos,
  mensaje: string,
): Promise<Response> {
  const contenido = JSON.stringify(datos, null, 2) + "\n";
  return fetch(`https://api.github.com/repos/${OWNER}/${REPO}/contents/${RUTA_ARCHIVO}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "User-Agent": USER_AGENT,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: mensaje,
      content: Buffer.from(contenido, "utf8").toString("base64"),
      sha,
      branch: RAMA,
    }),
  });
}

// `cambio` es el valor absoluto final para "guardar", o el delta a sumar/restar para
// "comprar"/"vender" — el promedio ponderado de costo base sale solo de acumular
// costo_base_usd en cada compra y restar la porción proporcional en cada venta, sin
// necesidad de guardar el historial de transacciones.
function calcularNuevo(actual: Posicion | undefined, accion: Accion, cambio: Posicion | null): Posicion | null {
  if (accion === "borrar") return null;
  if (accion === "guardar") return cambio as Posicion;

  const c = cambio as Posicion;
  if (accion === "comprar") {
    const base = actual ?? { acciones: 0, costo_base_usd: 0 };
    return { acciones: base.acciones + c.acciones, costo_base_usd: base.costo_base_usd + c.costo_base_usd };
  }

  // vender
  if (!actual) {
    throw new ErrorValidacion(`no hay una posición guardada de este ticker para vender`);
  }
  if (c.acciones > actual.acciones + EPSILON) {
    throw new ErrorValidacion("no puedes vender más acciones de las que tienes guardadas");
  }
  const accionesRestantes = actual.acciones - c.acciones;
  if (accionesRestantes <= EPSILON) return null; // vendiste todo
  return { acciones: accionesRestantes, costo_base_usd: actual.costo_base_usd - c.costo_base_usd };
}

async function aplicarCambio(
  token: string,
  ticker: string,
  accion: Accion,
  cambio: Posicion | null,
  reintentar = true,
): Promise<Datos> {
  const { sha, datos } = await leerArchivo(token);
  const nuevaPosicion = calcularNuevo(datos[ticker], accion, cambio);

  const nuevos = { ...datos };
  if (nuevaPosicion === null) {
    delete nuevos[ticker];
  } else {
    nuevos[ticker] = nuevaPosicion;
  }

  const mensaje = `mi-inversion: ${accion} ${ticker}`;
  const resp = await escribirArchivo(token, sha, nuevos, mensaje);

  if (resp.status === 409 && reintentar) {
    return aplicarCambio(token, ticker, accion, cambio, false);
  }
  if (!resp.ok) {
    throw new Error(`GitHub PUT ${resp.status}: ${await resp.text()}`);
  }

  return nuevos;
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const token = process.env.GITHUB_WRITE_TOKEN_PRIVADO;
  if (!token) {
    res.status(500).json({ error: "GITHUB_WRITE_TOKEN_PRIVADO no configurado" });
    return;
  }

  if (req.method === "GET") {
    try {
      const { datos } = await leerArchivo(token);
      res.status(200).json({ datos });
    } catch {
      res.status(502).json({ error: "no se pudo leer mi-inversion.json" });
    }
    return;
  }

  if (req.method === "POST") {
    const claveEsperada = process.env.WATCHLIST_EDIT_KEY;
    if (!claveEsperada) {
      res.status(500).json({ error: "WATCHLIST_EDIT_KEY no configurada" });
      return;
    }

    const body = (req.body ?? {}) as {
      ticker?: string;
      accion?: string;
      clave?: string;
      acciones?: number;
      costo_base_usd?: number;
    };

    if (body.clave !== claveEsperada) {
      res.status(401).json({ error: "clave incorrecta" });
      return;
    }

    const ticker = (body.ticker ?? "").trim().toUpperCase();
    if (!TICKER_VALIDO.test(ticker)) {
      res.status(400).json({ error: "ticker inválido" });
      return;
    }

    const accionesValidas: Accion[] = ["guardar", "comprar", "vender", "borrar"];
    if (!accionesValidas.includes(body.accion as Accion)) {
      res.status(400).json({ error: "accion inválida" });
      return;
    }
    const accion = body.accion as Accion;

    let cambio: Posicion | null = null;
    if (accion !== "borrar") {
      const acciones = Number(body.acciones);
      const costoBaseUsd = Number(body.costo_base_usd);
      if (!Number.isFinite(acciones) || acciones <= 0) {
        res.status(400).json({ error: "acciones inválido" });
        return;
      }
      if (!Number.isFinite(costoBaseUsd) || costoBaseUsd <= 0) {
        res.status(400).json({ error: "costo_base_usd inválido" });
        return;
      }
      cambio = { acciones, costo_base_usd: costoBaseUsd };
    }

    try {
      const datos = await aplicarCambio(token, ticker, accion, cambio);
      res.status(200).json({ datos });
    } catch (err) {
      if (err instanceof ErrorValidacion) {
        res.status(400).json({ error: err.message });
      } else {
        res.status(502).json({ error: "no se pudo actualizar mi-inversion.json" });
      }
    }
    return;
  }

  res.status(405).json({ error: "método no permitido" });
}
