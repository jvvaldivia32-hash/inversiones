import type { IncomingMessage, ServerResponse } from "node:http";

// Mismo patrón que web/api/watchlist.ts (leer ese archivo para el porqué de cada
// decisión: tipos mínimos sin @vercel/node, escritura vía GitHub Contents API con sha +
// reintento único en 409).
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
const RUTA_TESIS = "data/tesis.json";
const RUTA_DAILY = "data/daily.json";
const RAMA = "main";
const USER_AGENT = "inversiones-tesis-panel";
const TICKER_VALIDO = /^[A-Z0-9.]{1,10}$/;

// Heurística simple, no NLP — sección 7 del spec original: rechazar tesis que sean
// puramente sobre el precio en vez de sobre el negocio.
const FRASES_PROHIBIDAS = [
  "va a subir",
  "va a bajar",
  "esta barata",
  "esta cara",
  "se ve bien",
  "se ve mal",
  "al alza",
  "a la baja",
  "va a explotar",
  "va a caer",
];
const MINIMO_PALABRAS = 8;

interface ArchivoGitHub {
  sha: string;
  contenido: string;
}

async function leerArchivo(token: string, ruta: string): Promise<ArchivoGitHub> {
  const resp = await fetch(
    `https://api.github.com/repos/${OWNER}/${REPO}/contents/${ruta}?ref=${RAMA}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        "User-Agent": USER_AGENT,
        Accept: "application/vnd.github+json",
      },
    },
  );
  if (!resp.ok) {
    throw new Error(`GitHub GET ${ruta} ${resp.status}`);
  }
  const data = (await resp.json()) as { sha: string; content: string };
  const contenido = Buffer.from(data.content, "base64").toString("utf8");
  return { sha: data.sha, contenido };
}

async function escribirArchivo(
  token: string,
  ruta: string,
  sha: string,
  contenidoObjeto: unknown,
  mensaje: string,
): Promise<Response> {
  const contenido = JSON.stringify(contenidoObjeto, null, 2) + "\n";
  return fetch(`https://api.github.com/repos/${OWNER}/${REPO}/contents/${ruta}`, {
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

interface Tesis {
  id: string;
  ticker: string;
  texto: string;
  metrica_campo: string;
  metrica_tipo: "fundamental" | "segmento";
  umbral_verde: number;
  umbral_rojo: number;
  direccion: "mayor_es_mejor" | "menor_es_mejor";
  fecha_escrita: string;
  estado: "activa" | "cumplida" | "rota" | "cerrada";
  notas_cierre?: string;
  lecturas: unknown[];
}

const CAMPOS_FUNDAMENTAL = new Set([
  "ingresos_musd",
  "op_income_musd",
  "eps_gaap",
  "eps_non_gaap",
  "margen_operativo",
  "capex_musd",
  "flujo_op_musd",
]);

function esTextoVago(texto: string): boolean {
  const normalizado = texto.trim().toLowerCase();
  if (normalizado.split(/\s+/).filter(Boolean).length < MINIMO_PALABRAS) return true;
  return FRASES_PROHIBIDAS.some((frase) => normalizado.includes(frase));
}

async function metricaExiste(
  token: string,
  ticker: string,
  metricaTipo: string,
  metricaCampo: string,
): Promise<boolean> {
  const { contenido } = await leerArchivo(token, RUTA_DAILY);
  const daily = JSON.parse(contenido) as {
    posiciones?: {
      ticker: string;
      fundamentales?: { series?: Record<string, unknown[]> };
      segmentos?: { nombre: string }[];
    }[];
  };
  const posicion = daily.posiciones?.find((p) => p.ticker === ticker);
  if (!posicion) return false;

  if (metricaTipo === "fundamental") {
    if (!CAMPOS_FUNDAMENTAL.has(metricaCampo)) return false;
    const serie = posicion.fundamentales?.series?.[metricaCampo];
    return Array.isArray(serie) && serie.length > 0;
  }
  if (metricaTipo === "segmento") {
    return (posicion.segmentos ?? []).some((s) => s.nombre === metricaCampo);
  }
  return false;
}

async function crearTesis(
  token: string,
  body: Record<string, unknown>,
): Promise<{ status: number; payload: unknown }> {
  const ticker = String(body.ticker ?? "")
    .trim()
    .toUpperCase();
  const texto = String(body.texto ?? "").trim();
  const metricaCampo = String(body.metrica_campo ?? "").trim();
  const metricaTipo = body.metrica_tipo;
  const umbralVerde = Number(body.umbral_verde);
  const umbralRojo = Number(body.umbral_rojo);
  const direccion = body.direccion;

  if (!TICKER_VALIDO.test(ticker)) {
    return { status: 400, payload: { error: "ticker inválido" } };
  }
  if (esTextoVago(texto)) {
    return {
      status: 400,
      payload: { error: "la tesis tiene que ser sobre el negocio, no sobre el precio (mínimo 8 palabras)" },
    };
  }
  if (metricaTipo !== "fundamental" && metricaTipo !== "segmento") {
    return { status: 400, payload: { error: "metrica_tipo inválido" } };
  }
  if (!Number.isFinite(umbralVerde) || !Number.isFinite(umbralRojo)) {
    return { status: 400, payload: { error: "umbrales inválidos" } };
  }
  if (direccion !== "mayor_es_mejor" && direccion !== "menor_es_mejor") {
    return { status: 400, payload: { error: "direccion inválida" } };
  }
  if (!(await metricaExiste(token, ticker, metricaTipo, metricaCampo))) {
    return {
      status: 400,
      payload: { error: `"${metricaCampo}" no está entre los datos actuales de ${ticker}` },
    };
  }

  const { sha, contenido } = await leerArchivo(token, RUTA_TESIS);
  const lista = JSON.parse(contenido || "[]") as Tesis[];

  const fecha = new Date().toISOString().slice(0, 10);
  const idBase = `${ticker.toLowerCase()}-${metricaCampo.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  let id = `${idBase}-${fecha}`;
  let sufijo = 2;
  while (lista.some((t) => t.id === id)) {
    id = `${idBase}-${fecha}-${sufijo}`;
    sufijo += 1;
  }

  const nueva: Tesis = {
    id,
    ticker,
    texto,
    metrica_campo: metricaCampo,
    metrica_tipo: metricaTipo,
    umbral_verde: umbralVerde,
    umbral_rojo: umbralRojo,
    direccion,
    fecha_escrita: fecha,
    estado: "activa",
    lecturas: [],
  };

  const nuevaLista = [...lista, nueva];
  const resp = await escribirArchivo(token, RUTA_TESIS, sha, nuevaLista, `tesis: +${id}`);
  if (!resp.ok) {
    throw new Error(`GitHub PUT ${RUTA_TESIS} ${resp.status}: ${await resp.text()}`);
  }
  return { status: 200, payload: { tesis: nueva } };
}

async function cerrarTesis(
  token: string,
  body: Record<string, unknown>,
): Promise<{ status: number; payload: unknown }> {
  const id = String(body.id ?? "");
  const notasCierre = String(body.notas_cierre ?? "").trim();
  if (!id) {
    return { status: 400, payload: { error: "id requerido" } };
  }
  if (!notasCierre) {
    return { status: 400, payload: { error: "notas_cierre requerido — hay que decir por qué se cierra" } };
  }

  const { sha, contenido } = await leerArchivo(token, RUTA_TESIS);
  const lista = JSON.parse(contenido || "[]") as Tesis[];
  const objetivo = lista.find((t) => t.id === id);
  if (!objetivo) {
    return { status: 404, payload: { error: "tesis no encontrada" } };
  }

  // Regla dura: solo estado/notas_cierre se tocan. texto, métrica y umbrales quedan
  // intactos para siempre — "editar" es crear una tesis nueva, nunca esto.
  objetivo.estado = "cerrada";
  objetivo.notas_cierre = notasCierre;

  const resp = await escribirArchivo(token, RUTA_TESIS, sha, lista, `tesis: cerrar ${id}`);
  if (!resp.ok) {
    throw new Error(`GitHub PUT ${RUTA_TESIS} ${resp.status}: ${await resp.text()}`);
  }
  return { status: 200, payload: { tesis: objetivo } };
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const token = process.env.GITHUB_WRITE_TOKEN;
  if (!token) {
    res.status(500).json({ error: "GITHUB_WRITE_TOKEN no configurado" });
    return;
  }

  if (req.method === "GET") {
    try {
      const { contenido } = await leerArchivo(token, RUTA_TESIS);
      res.status(200).json({ tesis: JSON.parse(contenido || "[]") });
    } catch {
      res.status(502).json({ error: "no se pudo leer data/tesis.json" });
    }
    return;
  }

  if (req.method === "POST") {
    const claveEsperada = process.env.WATCHLIST_EDIT_KEY;
    if (!claveEsperada) {
      res.status(500).json({ error: "WATCHLIST_EDIT_KEY no configurada" });
      return;
    }
    const body = (req.body ?? {}) as Record<string, unknown>;
    if (body.clave !== claveEsperada) {
      res.status(401).json({ error: "clave incorrecta" });
      return;
    }

    try {
      const resultado =
        body.accion === "crear"
          ? await crearTesis(token, body)
          : body.accion === "cerrar"
            ? await cerrarTesis(token, body)
            : { status: 400, payload: { error: "accion inválida" } };
      res.status(resultado.status).json(resultado.payload);
    } catch {
      res.status(502).json({ error: "no se pudo actualizar data/tesis.json" });
    }
    return;
  }

  res.status(405).json({ error: "método no permitido" });
}
