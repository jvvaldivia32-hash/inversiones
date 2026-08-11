import type { IncomingMessage, ServerResponse } from "node:http";

// Tipos mínimos del runtime Node de Vercel: en producción el objeto real trae
// .status()/.json() y el body ya parseado como JSON, sin necesidad de instalar
// @vercel/node solo por los tipos (ver CLAUDE.md, evitar dependencias de más).
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
const RUTA_ARCHIVO = "watchlist.txt";
const RAMA = "main";
const USER_AGENT = "inversiones-watchlist-panel";
const TICKER_VALIDO = /^[A-Z0-9.]{1,10}$/;

interface ArchivoGitHub {
  sha: string;
  contenido: string;
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
  return { sha: data.sha, contenido };
}

function parseTickers(contenido: string): string[] {
  return contenido
    .split("\n")
    .map((l) => l.trim().toUpperCase())
    .filter(Boolean);
}

async function escribirArchivo(
  token: string,
  sha: string,
  tickersOrdenados: string[],
  mensaje: string,
): Promise<Response> {
  const contenido = tickersOrdenados.join("\n") + "\n";
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

async function aplicarCambio(
  token: string,
  ticker: string,
  accion: "agregar" | "quitar",
  reintentar = true,
): Promise<string[]> {
  const { sha, contenido } = await leerArchivo(token);
  const actuales = parseTickers(contenido);
  const yaEsta = actuales.includes(ticker);

  if (accion === "agregar" && yaEsta) return [...actuales].sort();
  if (accion === "quitar" && !yaEsta) return [...actuales].sort();

  const nuevos = (
    accion === "agregar" ? [...actuales, ticker] : actuales.filter((t) => t !== ticker)
  ).sort();

  const mensaje = `watchlist: ${accion === "agregar" ? "+" : "-"}${ticker}`;
  const resp = await escribirArchivo(token, sha, nuevos, mensaje);

  if (resp.status === 409 && reintentar) {
    // el sha quedó viejo por una carrera: releer y reintentar una sola vez
    return aplicarCambio(token, ticker, accion, false);
  }
  if (!resp.ok) {
    throw new Error(`GitHub PUT ${resp.status}: ${await resp.text()}`);
  }

  return nuevos;
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const token = process.env.GITHUB_WRITE_TOKEN;
  if (!token) {
    res.status(500).json({ error: "GITHUB_WRITE_TOKEN no configurado" });
    return;
  }

  if (req.method === "GET") {
    try {
      const { contenido } = await leerArchivo(token);
      res.status(200).json({ tickers: parseTickers(contenido).sort() });
    } catch {
      res.status(502).json({ error: "no se pudo leer la watchlist" });
    }
    return;
  }

  if (req.method === "POST") {
    const claveEsperada = process.env.WATCHLIST_EDIT_KEY;
    if (!claveEsperada) {
      res.status(500).json({ error: "WATCHLIST_EDIT_KEY no configurada" });
      return;
    }

    const body = (req.body ?? {}) as { ticker?: string; accion?: string; clave?: string };

    if (body.clave !== claveEsperada) {
      res.status(401).json({ error: "clave incorrecta" });
      return;
    }

    const ticker = (body.ticker ?? "").trim().toUpperCase();
    if (!TICKER_VALIDO.test(ticker)) {
      res.status(400).json({ error: "ticker inválido" });
      return;
    }

    if (body.accion !== "agregar" && body.accion !== "quitar") {
      res.status(400).json({ error: "accion inválida" });
      return;
    }

    try {
      const tickers = await aplicarCambio(token, ticker, body.accion);
      res.status(200).json({ tickers });
    } catch {
      res.status(502).json({ error: "no se pudo actualizar la watchlist" });
    }
    return;
  }

  res.status(405).json({ error: "método no permitido" });
}
