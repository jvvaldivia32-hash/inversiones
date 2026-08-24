// Rangos de referencia "libro de texto" para leer una métrica sin tener que saber de
// memoria qué es alto o bajo — pedido explícito de José (2026-08-19): no es una
// recomendación de compra/venta (esa es una regla dura del proyecto, ver CLAUDE.md), es
// dar la vara de medir para que el usuario juzgue el número él mismo. Los umbrales son
// heurísticas generales de finanzas (el tipo de cosa que enseñaría un curso básico de
// análisis fundamental), no calculadas por IA ni específicas de ninguna empresa — cero
// riesgo de alucinación, deterministas, gratis.
//
// A propósito NO se cubren acá métricas que dependen demasiado de la industria para tener
// un umbral general razonable (margen bruto, EV/Ingresos, EV/EBITDA, P/VL) — dar un rango
// "normal" ahí sería engañoso (un margen bruto de 30% es pésimo para software y buenísimo
// para un supermercado).
//
// ---------------------------------------------------------------------------------------
// SEÑAL POR MÉTRICA (agregado 2026-08-21, pedido de José)
//
// Cada lectura viene además con un `nivel` que la UI pinta como punto verde/ámbar/rojo.
// Esto es deliberadamente **por métrica y nada más**: nunca se suman los niveles ni se
// deriva de ellos un veredicto tipo "comprar" / "no comprar" / "7 de 10". La regla dura
// del Radar (CLAUDE.md) prohíbe generar texto de recomendación, y José la acotó
// explícitamente a esto: "no explícitamente COMPRA, sino buen X / mal X en datos
// específicos". Si alguna vez se agrega un puntaje agregado, eso ya es otra decisión y
// hay que preguntarle primero.
//
// Los cuatro niveles y qué significan de verdad:
//   bueno    → el número está del lado favorable de la vara de medir.
//   neutro   → está en el rango normal; no dice nada ni bueno ni malo (se pinta gris, sin
//              color, para no gastar señal de color en "no pasa nada").
//   atencion → no es necesariamente malo, pero hay algo que conviene mirar antes de
//              decidir (un P/E alto puede estar justificado por crecimiento; un beta alto
//              no es un defecto, es más volatilidad). Ámbar.
//   malo     → el número es malo por sí solo bajo cualquier lectura razonable (pierde
//              plata, ingresos cayendo). Rojo.
//
// El límite entre `atencion` y `malo` es donde está el juicio: valoración cara, mucha
// deuda o mucha volatilidad son `atencion`, no `malo`, porque son elecciones de perfil de
// inversión y no defectos del negocio. Rojo se reserva para "el negocio está perdiendo
// plata o encogiéndose".

export type NivelSenal = "bueno" | "neutro" | "atencion" | "malo";

export interface Lectura {
  texto: string;
  nivel: NivelSenal;
}

interface Tramo {
  desde: number;
  texto: string;
  nivel: NivelSenal;
}

function banda(valor: number, tramos: Tramo[]): Lectura {
  const ordenado = [...tramos].sort((a, b) => b.desde - a.desde);
  for (const t of ordenado) {
    if (valor >= t.desde) return { texto: t.texto, nivel: t.nivel };
  }
  // Fallback: solo se llega acá si ningún tramo cubre el valor, o sea si la tabla de
  // tramos no tiene un piso en -Infinity. Devolver el tramo más bajo sería mentir (fue
  // exactamente el bug de MCD: deuda/patrimonio -38,97 leído como "deuda baja"), así que
  // se admite no saber en vez de inventar una lectura.
  const ultimo = ordenado[ordenado.length - 1];
  return { texto: `fuera de los rangos de referencia habituales (bajo ${ultimo.desde})`, nivel: "atencion" };
}

export function contextoRoe(pct: number): Lectura {
  return banda(pct, [
    { desde: 25, texto: "muy alto — el promedio del S&P 500 ronda 15-18%", nivel: "bueno" },
    { desde: 15, texto: "alto, sobre el promedio del mercado (~15-18%)", nivel: "bueno" },
    { desde: 8, texto: "normal, cerca del promedio del mercado", nivel: "neutro" },
    { desde: 0, texto: "bajo respecto al promedio del mercado", nivel: "atencion" },
    { desde: -Infinity, texto: "negativo — la empresa perdió dinero ese período", nivel: "malo" },
  ]);
}

export function contextoRoicRoce(pct: number): Lectura {
  return banda(pct, [
    {
      desde: 15,
      texto: "alto — típicamente se considera que crea valor si supera el costo de capital (~8-10%)",
      nivel: "bueno",
    },
    { desde: 8, texto: "normal, cerca del costo de capital típico (~8-10%)", nivel: "neutro" },
    { desde: 0, texto: "bajo — apenas cubre o no cubre el costo de capital típico", nivel: "atencion" },
    { desde: -Infinity, texto: "negativo", nivel: "malo" },
  ]);
}

export function contextoMargenOperativo(pct: number): Lectura {
  return banda(pct, [
    { desde: 20, texto: "alto — sobre 20% suele considerarse un negocio muy rentable", nivel: "bueno" },
    { desde: 10, texto: "normal, en el rango típico de la mayoría de industrias", nivel: "neutro" },
    { desde: 0, texto: "bajo — margen operativo ajustado", nivel: "atencion" },
    { desde: -Infinity, texto: "negativo — pierde plata en su operación", nivel: "malo" },
  ]);
}

export function contextoDeudaPatrimonio(valor: number): Lectura {
  return banda(valor, [
    { desde: 2, texto: "alto — nivel de deuda considerable frente a su patrimonio", nivel: "atencion" },
    { desde: 1, texto: "moderado", nivel: "neutro" },
    { desde: 0, texto: "bajo — poca deuda frente a su patrimonio", nivel: "bueno" },
    // Patrimonio contable negativo: la razón se vuelve un número negativo sin sentido
    // financiero directo (MCD, HD, SBUX, PM viven así). No es señal de quiebra — es el
    // resultado de años de recompras de acciones por sobre el patrimonio contable — pero
    // tampoco es "deuda baja", que es justo lo que mostraba antes de este arreglo.
    {
      desde: -Infinity,
      texto:
        "patrimonio contable negativo — pasa cuando la empresa recompró acciones por más de lo que vale su patrimonio en libros (McDonald's, Home Depot y Starbucks están así). La razón deuda/patrimonio no se puede leer acá; mirá deuda neta / EBITDA en su lugar",
      nivel: "atencion",
    },
  ]);
}

export function contextoDeudaNetaEbitda(veces: number): Lectura {
  return banda(veces, [
    {
      desde: 4,
      texto: "alto — regla de pulgar típica de análisis crediticio ve riesgo sobre 4x",
      nivel: "atencion",
    },
    { desde: 2, texto: "moderado", nivel: "neutro" },
    { desde: 0, texto: "bajo/saludable, bajo 2x", nivel: "bueno" },
    // Deuda neta negativa = tiene más caja que deuda. Es la posición financiera más
    // cómoda posible, no un dato raro (AAPL y GOOGL están así).
    {
      desde: -Infinity,
      texto: "deuda neta negativa — tiene más caja e inversiones líquidas que deuda total",
      nivel: "bueno",
    },
  ]);
}

export function contextoPE(veces: number): Lectura {
  return banda(veces, [
    {
      desde: 35,
      texto:
        "alto — el promedio histórico del S&P 500 ronda 15-20x (aunque empresas de alto crecimiento suelen justificar un P/E más alto)",
      nivel: "atencion",
    },
    { desde: 25, texto: "por sobre el promedio histórico del mercado (~15-20x)", nivel: "atencion" },
    { desde: 15, texto: "cerca del promedio histórico del mercado (~15-20x)", nivel: "neutro" },
    { desde: 0, texto: "bajo respecto al promedio histórico del mercado", nivel: "bueno" },
    {
      desde: -Infinity,
      texto: "negativo — la empresa perdió dinero, el P/E no aplica bien acá",
      nivel: "malo",
    },
  ]);
}

export function contextoDividendYield(pct: number): Lectura {
  return banda(pct, [
    {
      desde: 4,
      texto:
        "alto — un yield así de alto a veces es señal de que el mercado espera un recorte, vale la pena revisar el payout ratio",
      nivel: "atencion",
    },
    { desde: 2, texto: "normal", nivel: "bueno" },
    { desde: 0.01, texto: "bajo", nivel: "neutro" },
    // No repartir dividendos no es bueno ni malo: es una decisión de reinvertir (GOOGL y
    // AMZN no repartieron por décadas). Neutro a propósito.
    { desde: -Infinity, texto: "no reparte dividendos", nivel: "neutro" },
  ]);
}

export function contextoPayoutRatio(pct: number): Lectura {
  return banda(pct, [
    {
      desde: 90,
      texto: "muy alto — reparte casi todo lo que gana, poco margen si bajan las utilidades",
      nivel: "atencion",
    },
    { desde: 60, texto: "alto", nivel: "atencion" },
    { desde: 30, texto: "balanceado entre repartir y reinvertir", nivel: "bueno" },
    { desde: -Infinity, texto: "conservador — reinvierte la mayoría de sus utilidades", nivel: "neutro" },
  ]);
}

export function contextoBeta(valor: number): Lectura {
  return banda(valor, [
    {
      desde: 1.3,
      texto: "alta volatilidad — se mueve bastante más que el mercado en general",
      nivel: "atencion",
    },
    { desde: 0.8, texto: "similar al mercado en general", nivel: "neutro" },
    {
      desde: -Infinity,
      texto: "baja volatilidad — se mueve menos que el mercado en general",
      nivel: "neutro",
    },
  ]);
}

export function contextoCrecimientoIngresos(pct: number): Lectura {
  return banda(pct, [
    { desde: 20, texto: "crecimiento alto", nivel: "bueno" },
    { desde: 5, texto: "crecimiento saludable", nivel: "bueno" },
    { desde: 0, texto: "crecimiento lento", nivel: "atencion" },
    { desde: -Infinity, texto: "ingresos cayendo interanual", nivel: "malo" },
  ]);
}
