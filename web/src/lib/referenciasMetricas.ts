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

interface Tramo {
  desde: number;
  texto: string;
}

function banda(valor: number, tramos: Tramo[]): string {
  const ordenado = [...tramos].sort((a, b) => b.desde - a.desde);
  for (const t of ordenado) {
    if (valor >= t.desde) return t.texto;
  }
  return ordenado[ordenado.length - 1].texto;
}

export function contextoRoe(pct: number): string {
  return banda(pct, [
    { desde: 25, texto: "muy alto — el promedio del S&P 500 ronda 15-18%" },
    { desde: 15, texto: "alto, sobre el promedio del mercado (~15-18%)" },
    { desde: 8, texto: "normal, cerca del promedio del mercado" },
    { desde: 0, texto: "bajo respecto al promedio del mercado" },
    { desde: -Infinity, texto: "negativo — la empresa perdió dinero ese período" },
  ]);
}

export function contextoRoicRoce(pct: number): string {
  return banda(pct, [
    { desde: 15, texto: "alto — típicamente se considera que crea valor si supera el costo de capital (~8-10%)" },
    { desde: 8, texto: "normal, cerca del costo de capital típico (~8-10%)" },
    { desde: 0, texto: "bajo — apenas cubre o no cubre el costo de capital típico" },
    { desde: -Infinity, texto: "negativo" },
  ]);
}

export function contextoMargenOperativo(pct: number): string {
  return banda(pct, [
    { desde: 20, texto: "alto — sobre 20% suele considerarse un negocio muy rentable" },
    { desde: 10, texto: "normal, en el rango típico de la mayoría de industrias" },
    { desde: 0, texto: "bajo — margen operativo ajustado" },
    { desde: -Infinity, texto: "negativo — pierde plata en su operación" },
  ]);
}

export function contextoDeudaPatrimonio(valor: number): string {
  return banda(valor, [
    { desde: 2, texto: "alto — nivel de deuda considerable frente a su patrimonio" },
    { desde: 1, texto: "moderado" },
    { desde: 0, texto: "bajo — poca deuda frente a su patrimonio" },
  ]);
}

export function contextoDeudaNetaEbitda(veces: number): string {
  return banda(veces, [
    { desde: 4, texto: "alto — regla de pulgar típica de análisis crediticio ve riesgo sobre 4x" },
    { desde: 2, texto: "moderado" },
    { desde: -Infinity, texto: "bajo/saludable, bajo 2x" },
  ]);
}

export function contextoPE(veces: number): string {
  return banda(veces, [
    { desde: 35, texto: "alto — el promedio histórico del S&P 500 ronda 15-20x (aunque empresas de alto crecimiento suelen justificar un P/E más alto)" },
    { desde: 25, texto: "por sobre el promedio histórico del mercado (~15-20x)" },
    { desde: 15, texto: "cerca del promedio histórico del mercado (~15-20x)" },
    { desde: 0, texto: "bajo respecto al promedio histórico del mercado" },
    { desde: -Infinity, texto: "negativo — la empresa perdió dinero, el P/E no aplica bien acá" },
  ]);
}

export function contextoDividendYield(pct: number): string {
  return banda(pct, [
    { desde: 4, texto: "alto — un yield así de alto a veces es señal de que el mercado espera un recorte, vale la pena revisar el payout ratio" },
    { desde: 2, texto: "normal" },
    { desde: 0.01, texto: "bajo" },
    { desde: -Infinity, texto: "no reparte dividendos" },
  ]);
}

export function contextoPayoutRatio(pct: number): string {
  return banda(pct, [
    { desde: 90, texto: "muy alto — reparte casi todo lo que gana, poco margen si bajan las utilidades" },
    { desde: 60, texto: "alto" },
    { desde: 30, texto: "balanceado entre repartir y reinvertir" },
    { desde: -Infinity, texto: "conservador — reinvierte la mayoría de sus utilidades" },
  ]);
}

export function contextoBeta(valor: number): string {
  return banda(valor, [
    { desde: 1.3, texto: "alta volatilidad — se mueve bastante más que el mercado en general" },
    { desde: 0.8, texto: "similar al mercado en general" },
    { desde: -Infinity, texto: "baja volatilidad — se mueve menos que el mercado en general" },
  ]);
}

export function contextoCrecimientoIngresos(pct: number): string {
  return banda(pct, [
    { desde: 20, texto: "crecimiento alto" },
    { desde: 5, texto: "crecimiento saludable" },
    { desde: 0, texto: "crecimiento lento" },
    { desde: -Infinity, texto: "ingresos cayendo interanual" },
  ]);
}
