import type { IncomingMessage, ServerResponse } from "node:http";

// Simulador de cartera ficticia ("paper investing") — extra fuera del plan madre, pedido
// por José 2026-08-20. A diferencia de mi-inversion.ts, acá NO hay plata real que proteger
// (parte de $5.000 ficticios + "sueldo" simulado de collector/paper_aporte_mensual.py), así
// que este archivo vive en el repo PÚBLICO principal, mismo patrón que watchlist.ts/
// tesis.ts (GITHUB_WRITE_TOKEN, no el _PRIVADO). La clave de edición sí se reutiliza
// (WATCHLIST_EDIT_KEY) — mismo candado mínimo de "app de un solo usuario" que ya existe.
//
// Diferencia real de negocio respecto a mi-inversion.ts: acá hay un saldo de efectivo
// (`saldo_no_invertido_usd`) del que salen las compras y al que vuelven las ventas — en
// mi-inversion.ts no existe ese concepto porque cada compra ahí es plata real que el
// usuario deposita en el momento, no un pool limitado.
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
const RUTA_ARCHIVO = "data/paperinvesting.json";
const RAMA = "main";
const USER_AGENT = "inversiones-paperinvesting-panel";
const TICKER_VALIDO = /^[A-Z0-9.]{1,10}$/;

// Mismo criterio que mi-inversion.ts: se guarda acciones + costo base, no el monto que
// tipea el usuario tal cual — se recalcula en vivo contra el precio actual.
interface Posicion {
  acciones: number;
  costo_base_usd: number;
}

interface Aporte {
  fecha: string;
  monto_usd: number;
}

interface Estado {
  fecha_inicio: string;
  saldo_no_invertido_usd: number;
  aportes: Aporte[];
  posiciones: Record<string, Posicion>;
}

type Accion = "comprar" | "vender";

// Distingue un rechazo de negocio (no alcanza el efectivo, venta mayor a lo que hay) de una
// falla real de GitHub — el handler los traduce a 400 vs 502.
class ErrorValidacion extends Error {}

// Tolerancia para "vendí todo"/"gasté todo el efectivo": floats nunca calzan exacto entre
// lo que computó el navegador y lo que hay guardado.
const EPSILON = 1e-6;

interface ArchivoGitHub {
  sha: string;
  estado: Estado;
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
  const estado = JSON.parse(contenido) as Estado;
  return { sha: data.sha, estado };
}

async function escribirArchivo(
  token: string,
  sha: string,
  estado: Estado,
  mensaje: string,
): Promise<Response> {
  const contenido = JSON.stringify(estado, null, 2) + "\n";
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

// `cambio` es lo que el navegador ya calculó a partir del precio actual (mismo modelo de
// confianza que mi-inversion.ts: no hay validación de precio server-side, es una app de un
// solo usuario detrás de clave compartida).
function aplicarAccion(estado: Estado, ticker: string, accion: Accion, cambio: Posicion): Estado {
  const actual = estado.posiciones[ticker];
  const nuevasPosiciones = { ...estado.posiciones };
  let saldo = estado.saldo_no_invertido_usd;

  if (accion === "comprar") {
    if (cambio.costo_base_usd > saldo + EPSILON) {
      throw new ErrorValidacion("no te alcanza el efectivo disponible");
    }
    saldo -= cambio.costo_base_usd;
    const base = actual ?? { acciones: 0, costo_base_usd: 0 };
    nuevasPosiciones[ticker] = {
      acciones: base.acciones + cambio.acciones,
      costo_base_usd: base.costo_base_usd + cambio.costo_base_usd,
    };
  } else {
    if (!actual) {
      throw new ErrorValidacion("no hay una posición guardada de este ticker para vender");
    }
    if (cambio.acciones > actual.acciones + EPSILON) {
      throw new ErrorValidacion("no puedes vender más acciones de las que tienes guardadas");
    }
    saldo += cambio.costo_base_usd;
    const accionesRestantes = actual.acciones - cambio.acciones;
    if (accionesRestantes <= EPSILON) {
      delete nuevasPosiciones[ticker];
    } else {
      nuevasPosiciones[ticker] = {
        acciones: accionesRestantes,
        costo_base_usd: actual.costo_base_usd - cambio.costo_base_usd,
      };
    }
  }

  return { ...estado, saldo_no_invertido_usd: saldo, posiciones: nuevasPosiciones };
}

async function aplicarCambio(
  token: string,
  ticker: string,
  accion: Accion,
  cambio: Posicion,
  reintentar = true,
): Promise<Estado> {
  const { sha, estado } = await leerArchivo(token);
  const nuevoEstado = aplicarAccion(estado, ticker, accion, cambio);

  const mensaje = `paperinvesting: ${accion} ${ticker}`;
  const resp = await escribirArchivo(token, sha, nuevoEstado, mensaje);

  if (resp.status === 409 && reintentar) {
    return aplicarCambio(token, ticker, accion, cambio, false);
  }
  if (!resp.ok) {
    throw new Error(`GitHub PUT ${resp.status}: ${await resp.text()}`);
  }

  return nuevoEstado;
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const token = process.env.GITHUB_WRITE_TOKEN;
  if (!token) {
    res.status(500).json({ error: "GITHUB_WRITE_TOKEN no configurado" });
    return;
  }

  if (req.method === "GET") {
    try {
      const { estado } = await leerArchivo(token);
      res.status(200).json(estado);
    } catch {
      res.status(502).json({ error: "no se pudo leer data/paperinvesting.json" });
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

    const accionesValidas: Accion[] = ["comprar", "vender"];
    if (!accionesValidas.includes(body.accion as Accion)) {
      res.status(400).json({ error: "accion inválida" });
      return;
    }
    const accion = body.accion as Accion;

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

    try {
      const estado = await aplicarCambio(token, ticker, accion, { acciones, costo_base_usd: costoBaseUsd });
      res.status(200).json(estado);
    } catch (err) {
      if (err instanceof ErrorValidacion) {
        res.status(400).json({ error: err.message });
      } else {
        res.status(502).json({ error: "no se pudo actualizar data/paperinvesting.json" });
      }
    }
    return;
  }

  res.status(405).json({ error: "método no permitido" });
}
