import type { IncomingMessage, ServerResponse } from "node:http";

// Mismo patrón que web/api/watchlist.ts (leer ese archivo para el porqué de cada
// decisión general: tipos mínimos sin @vercel/node, escritura vía GitHub Contents API
// con sha + reintento único en 409).
//
// Diferencia a propósito respecto a watchlist.ts/tesis.ts: NO hay clave compartida acá.
// El límite real contra abuso es que este endpoint nunca deja crear un `id` nuevo, solo
// editar uno de los que ya existen en data/amigos.json (provisionados a mano) — así que
// aunque alguien encuentre la URL de un amigo sin querer, lo peor que puede hacer es
// cambiarle los seguimientos a ESE amigo puntual, nunca agregar amigos nuevos ni tocar
// la watchlist real. Un cooldown de 60s por id evita además que alguien lo deje
// cambiando en loop.
interface VercelRequest extends IncomingMessage {
  method?: string;
  body?: unknown;
}

interface VercelResponse extends ServerResponse {
  status(code: number): VercelResponse;
  json(body: unknown): VercelResponse;
}

const OWNER = "jvvaldivia32-hash";
const REPO = "inversiones";
const RUTA_ARCHIVO = "data/amigos.json";
const RAMA = "main";
const USER_AGENT = "inversiones-amigos-panel";
const TICKER_VALIDO = /^[A-Z0-9.]{1,10}$/;
const MAX_SEGUIMIENTOS = 4;
const MAX_TICKERS = 2;
const MAX_PALABRA_CLAVE = 40;
const MAX_NOMBRE = 20;
const COOLDOWN_MS = 60_000;

type Seguimiento = { tipo: "ticker" | "palabra_clave"; valor: string };

interface AmigoConfig {
  id: string;
  nombre: string;
  // Gate de contraseña por amigo en el frontend (Amigos.tsx) — plaintext a propósito, no
  // es autenticación real, solo evita que se confundan editando la tarjeta del otro
  // (decisión explícita 2026-08-15). Tiene que sobrevivir cada guardado o desaparecería
  // la primera vez que alguien editara sus seguimientos.
  clave?: string;
  seguimientos: Seguimiento[];
  ultima_edicion?: string;
}

interface ArchivoAmigos {
  sha: string;
  amigos: AmigoConfig[];
}

async function leerArchivo(token: string): Promise<ArchivoAmigos> {
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
  return { sha: data.sha, amigos: JSON.parse(contenido) as AmigoConfig[] };
}

async function escribirArchivo(
  token: string,
  sha: string,
  amigos: AmigoConfig[],
  mensaje: string,
): Promise<Response> {
  const contenido = JSON.stringify(amigos, null, 2) + "\n";
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

class ErrorConocido extends Error {}

async function aplicarCambio(
  token: string,
  id: string,
  cambios: { nombre?: string; seguimientos: Seguimiento[] },
  reintentar = true,
): Promise<AmigoConfig[]> {
  const { sha, amigos } = await leerArchivo(token);
  const indice = amigos.findIndex((a) => a.id === id);
  if (indice === -1) {
    throw new ErrorConocido("id desconocido");
  }

  const actual = amigos[indice];
  if (actual.ultima_edicion) {
    const desdeMs = Date.now() - new Date(actual.ultima_edicion).getTime();
    if (desdeMs >= 0 && desdeMs < COOLDOWN_MS) {
      throw new ErrorConocido("cooldown");
    }
  }

  const actualizado: AmigoConfig = {
    id: actual.id,
    nombre: cambios.nombre || actual.nombre,
    clave: actual.clave,
    seguimientos: cambios.seguimientos,
    ultima_edicion: new Date().toISOString(),
  };
  const nuevos = [...amigos];
  nuevos[indice] = actualizado;

  const mensaje = `amigos: ${actualizado.nombre} actualizó sus seguimientos`;
  const resp = await escribirArchivo(token, sha, nuevos, mensaje);

  if (resp.status === 409 && reintentar) {
    // el sha quedó viejo por una carrera: releer y reintentar una sola vez
    return aplicarCambio(token, id, cambios, false);
  }
  if (!resp.ok) {
    throw new Error(`GitHub PUT ${resp.status}: ${await resp.text()}`);
  }

  return nuevos;
}

function validarSeguimientos(input: unknown): Seguimiento[] | null {
  if (!Array.isArray(input)) return null;

  const validos: Seguimiento[] = [];
  let tickers = 0;

  for (const item of input) {
    if (typeof item !== "object" || item === null) continue;
    const tipo = (item as { tipo?: unknown }).tipo;
    const valorCrudo = (item as { valor?: unknown }).valor;

    if (tipo === "ticker") {
      if (tickers >= MAX_TICKERS) continue;
      const valor = String(valorCrudo ?? "").trim().toUpperCase();
      if (!TICKER_VALIDO.test(valor)) continue;
      validos.push({ tipo: "ticker", valor });
      tickers += 1;
    } else if (tipo === "palabra_clave") {
      const valor = String(valorCrudo ?? "").trim().slice(0, MAX_PALABRA_CLAVE);
      if (!valor) continue;
      validos.push({ tipo: "palabra_clave", valor });
    }

    if (validos.length >= MAX_SEGUIMIENTOS) break;
  }

  return validos;
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const token = process.env.GITHUB_WRITE_TOKEN;
  if (!token) {
    res.status(500).json({ error: "GITHUB_WRITE_TOKEN no configurado" });
    return;
  }

  if (req.method !== "POST") {
    res.status(405).json({ error: "método no permitido" });
    return;
  }

  const body = (req.body ?? {}) as {
    id?: string;
    nombre?: string;
    seguimientos?: unknown;
  };

  const id = String(body.id ?? "").trim();
  if (!id) {
    res.status(400).json({ error: "id requerido" });
    return;
  }

  const nombre = body.nombre ? String(body.nombre).trim().slice(0, MAX_NOMBRE) : undefined;

  const seguimientos = validarSeguimientos(body.seguimientos);
  if (!seguimientos || seguimientos.length === 0) {
    res.status(400).json({
      error: `al menos un seguimiento válido (ticker o palabra clave, máx. ${MAX_SEGUIMIENTOS})`,
    });
    return;
  }

  try {
    const amigos = await aplicarCambio(token, id, { nombre, seguimientos });
    res.status(200).json({ ok: true, amigos });
  } catch (e) {
    if (e instanceof ErrorConocido && e.message === "id desconocido") {
      res.status(404).json({ error: "ese link no corresponde a ningún amigo conocido" });
      return;
    }
    if (e instanceof ErrorConocido && e.message === "cooldown") {
      res.status(429).json({ error: "espera un minuto antes de volver a editar" });
      return;
    }
    res.status(502).json({ error: "no se pudo actualizar" });
  }
}
