// Definiciones propias, no copiadas de ningún lado — mismo criterio de "reescribir con
// tus palabras" que el resto del proyecto usa para noticias. `campoEjemplo` deja que el
// componente busque un valor real y actual de tu propia watchlist en vez de un número
// inventado que se vuelve viejo — mismo espíritu que "ningún número sin su fuente".

export type CampoFundamentalEjemplo =
  | "ingresos_musd"
  | "op_income_musd"
  | "eps_gaap"
  | "margen_operativo"
  | "capex_musd"
  | "flujo_op_musd";

// Campos de MetricasAvanzadas (collector/sources/metricas_avanzadas.py) — mismo mecanismo
// que campoEjemplo pero buscando en posicion.metricas_avanzadas en vez de
// posicion.fundamentales.series.
export type CampoMetricaAvanzadaEjemplo =
  | "market_cap_musd"
  | "enterprise_value_musd"
  | "deuda_neta_musd"
  | "deuda_neta_ebitda"
  | "margen_bruto_pct"
  | "margen_ebit_pct"
  | "roa_pct"
  | "roe_pct"
  | "roic_pct"
  | "roce_pct"
  | "pe"
  | "ev_ingresos"
  | "ev_ebitda"
  | "p_vl"
  | "dividend_yield_pct"
  | "payout_ratio_pct"
  | "beta";

export interface EntradaDiccionario {
  id: string;
  termino: string;
  definicion: string;
  campoEjemplo?: CampoFundamentalEjemplo;
  campoMetricaAvanzada?: CampoMetricaAvanzadaEjemplo;
  esDeudaPatrimonio?: boolean;
}

export const DICCIONARIO: EntradaDiccionario[] = [
  {
    id: "ingresos",
    termino: "Ingresos",
    definicion:
      "Todo lo que la empresa factura por vender su producto o servicio, antes de descontar ningún costo. No es ganancia — es lo que entra por la puerta.",
    campoEjemplo: "ingresos_musd",
  },
  {
    id: "operating-income",
    termino: "Operating income",
    definicion:
      "Lo que le queda a la empresa después de restarle a los ingresos los costos de operar el negocio (producción, sueldos, marketing), pero antes de intereses e impuestos.",
    campoEjemplo: "op_income_musd",
  },
  {
    id: "margen-operativo",
    termino: "Margen operativo",
    definicion:
      "El operating income como porcentaje de los ingresos. Un margen de 45% significa que por cada US$100 que factura, le quedan US$45 de ganancia operativa antes de intereses e impuestos.",
    campoEjemplo: "margen_operativo",
  },
  {
    id: "eps",
    termino: "EPS (Earnings Per Share)",
    definicion:
      "La ganancia neta de la empresa dividida por el número de acciones en circulación — cuánto ganó por cada acción que existe. El \"diluido\" (el que se muestra acá) también cuenta las acciones que podrían emitirse a futuro (opciones, bonos convertibles), por eso suele ser un poco menor al EPS básico.",
    campoEjemplo: "eps_gaap",
  },
  {
    id: "capex",
    termino: "Capex (Capital expenditures)",
    definicion:
      "Plata que la empresa gasta en activos físicos o de largo plazo — equipos, centros de datos, plantas — para mantener o hacer crecer el negocio. No es gasto del día a día, es inversión que se recupera en años.",
    campoEjemplo: "capex_musd",
  },
  {
    id: "flujo-operativo",
    termino: "Flujo operativo",
    definicion:
      "Plata que efectivamente entra a la caja por operar el negocio — no ganancia contable, plata real — antes de gastos de inversión o financiamiento. Si es negativo, la empresa está quemando caja para seguir operando: señal de alerta.",
    campoEjemplo: "flujo_op_musd",
  },
  {
    id: "deuda-patrimonio",
    termino: "Deuda/patrimonio",
    definicion:
      "Cuánta deuda de largo plazo tiene la empresa comparada con lo que vale su patrimonio (activos menos pasivos). Un ratio de 0,3 significa que la deuda es 30% del patrimonio — sano. El Radar descarta sobre 2 (debe el doble de lo que vale). Excepción: bancos, donde la deuda es el modelo de negocio (los depósitos son pasivo) — ahí este número no se evalúa igual.",
    esDeudaPatrimonio: true,
  },
  {
    id: "ipo",
    termino: "IPO (oferta pública inicial)",
    definicion:
      "El momento en que una empresa privada empieza a vender acciones al público por primera vez, listándose en una bolsa. Antes de eso sus dueños son privados (fundadores, fondos de capital de riesgo); después, cualquiera puede comprar una acción.",
  },
  {
    id: "tesis",
    termino: "Tesis",
    definicion:
      "Lo que creés que va a pasar en el negocio de una empresa, escrito ANTES de invertir, con un número concreto que la confirme o la refute. No es \"va a subir\" — es \"creo que Azure va a seguir creciendo sobre 35%; si cae bajo 25%, me equivoqué\".",
  },
  {
    id: "semaforo",
    termino: "Semáforo (de una tesis)",
    definicion:
      "Verde: la tesis se sigue cumpliendo según el último dato real. Ámbar: zona gris, para revisar. Rojo: el número real quedó bajo el umbral que vos mismo definiste al escribirla — la tesis se rompió.",
  },
  {
    id: "castigada",
    termino: "Castigada (Radar)",
    definicion:
      "Un ticker cuyo precio está bajo el 85% de su máximo de las últimas 52 semanas, o bajo su promedio móvil de 200 días. No dice si conviene comprarla, solo que el precio bajó bastante — después se cruza contra \"sana\" para separar bache temporal de deterioro real.",
  },
  {
    id: "sana",
    termino: "Sana (Radar)",
    definicion:
      "Una empresa castigada en precio que igual tiene ingresos creciendo, margen operativo positivo, flujo de caja positivo y deuda controlada. Es la mitad del filtro que separa \"buena empresa en un mal momento\" de \"empresa realmente en problemas\".",
  },
  {
    id: "filings",
    termino: "10-K / 10-Q / 8-K",
    definicion:
      "Documentos que toda empresa que cotiza en EEUU está obligada a presentar ante la SEC (el regulador). El 10-K es el reporte anual completo, el 10-Q el trimestral, y el 8-K es un aviso puntual de un hecho relevante — ahí es donde sale el comunicado de resultados con las cifras por segmento. Todos son públicos y gratis en sec.gov.",
  },
  {
    id: "segmento",
    termino: "Segmento",
    definicion:
      "Una parte del negocio que la empresa separa al reportar (ej. \"Azure\" dentro de Microsoft, o \"ventas comparables en EEUU\" dentro de McDonald's). No siempre viene en las cifras contables oficiales — a veces solo se menciona en prosa dentro del comunicado de resultados, por eso se extrae de ahí en vez de la tabla de Fundamentales.",
  },
  {
    id: "yoy",
    termino: "YoY (year over year)",
    definicion:
      "Comparación contra el mismo período del año anterior, no contra el trimestre inmediatamente anterior. Sirve para no confundir una caída estacional normal (ej. ventas de retail después de diciembre) con un problema real del negocio.",
  },
  {
    id: "adr",
    termino: "ADR (American Depositary Receipt)",
    definicion:
      "Un certificado que representa acciones de una empresa extranjera, pero que se compra y vende en una bolsa de EEUU como una acción normal. Por eso se puede comprar Toyota o Nintendo sin tener una cuenta de corretaje japonesa — el ADR hace de intermediario.",
  },
  {
    id: "cobertura-unilateral",
    termino: "Cobertura unilateral",
    definicion:
      "Cuando una noticia la reportó un solo grupo editorial, sin que otro medio de una línea editorial distinta la haya confirmado todavía. No significa que sea falsa — solo que conviene esperar más fuentes antes de darla por sentada del todo.",
  },
  // A partir de acá: términos de "Métricas avanzadas" (extra fuera del plan madre,
  // 2026-08-14). Definiciones escritas contra lo que collector/sources/metricas_avanzadas.py
  // calcula de verdad, no contra la definición de libro de texto — donde el cálculo real se
  // simplifica o se aparta de la versión "oficial", se dice explícitamente.
  {
    id: "market-cap",
    termino: "Market cap",
    definicion:
      "El precio de la acción multiplicado por las acciones en circulación — cuánto costaría comprar la empresa entera al precio de bolsa de hoy. No es necesariamente lo que la empresa \"vale de verdad\", es lo que el mercado está dispuesto a pagar hoy.",
    campoMetricaAvanzada: "market_cap_musd",
  },
  {
    id: "enterprise-value",
    termino: "Enterprise value (EV)",
    definicion:
      "Market cap más la deuda neta. Es lo que realmente te llevás si compraras la empresa completa: pagas las acciones, pero heredas su deuda (y te quedas con su caja). Por eso se usa para comparar empresas con niveles de deuda distintos — el market cap solo no alcanza para eso.",
    campoMetricaAvanzada: "enterprise_value_musd",
  },
  {
    id: "deuda-neta",
    termino: "Deuda neta",
    definicion:
      "Deuda de corto más largo plazo, menos la caja disponible. Si sale negativa, la empresa tiene más plata en caja que deuda — no le debe nada a nadie en términos netos.",
    campoMetricaAvanzada: "deuda_neta_musd",
  },
  {
    id: "ebitda",
    termino: "EBITDA",
    definicion:
      "Operating income más depreciación y amortización — una forma de aproximar cuánta caja genera el negocio antes de restar gastos contables que no son plata saliendo de la caja ese año. No aparece solo en el panel de métricas, pero es la base de \"Deuda neta/EBITDA\" y \"EV/EBITDA\".",
  },
  {
    id: "deuda-neta-ebitda",
    termino: "Deuda neta / EBITDA",
    definicion:
      "Cuántos años de EBITDA le tomaría a la empresa pagar toda su deuda neta si destinara el 100% de esa caja solo a eso. Bajo 2x se considera cómodo; sobre 4x empieza a ser señal de alerta real.",
    campoMetricaAvanzada: "deuda_neta_ebitda",
  },
  {
    id: "margen-bruto",
    termino: "Margen bruto",
    definicion:
      "La utilidad bruta (ingresos menos el costo directo de producir lo que vende) como porcentaje de los ingresos. Mide qué tan cara es la operación más básica del negocio, antes de sueldos administrativos, marketing o I+D.",
    campoMetricaAvanzada: "margen_bruto_pct",
  },
  {
    id: "margen-ebit",
    termino: "Margen EBIT",
    definicion:
      "Acá es exactamente el mismo dato que \"Margen operativo\" (mismo cálculo, mismo valor) — se repite bajo este nombre en el panel de métricas avanzadas para poder compararlo de un vistazo junto al resto de los ratios de rentabilidad, no porque sea un número distinto.",
    campoMetricaAvanzada: "margen_ebit_pct",
  },
  {
    id: "roa",
    termino: "ROA (Return on Assets)",
    definicion:
      "Utilidad neta de los últimos 12 meses dividida por los activos totales de la empresa. Mide qué tan bien se usa TODO lo que la empresa tiene (propio y financiado con deuda) para generar ganancia.",
    campoMetricaAvanzada: "roa_pct",
  },
  {
    id: "roe",
    termino: "ROE (Return on Equity)",
    definicion:
      "Utilidad neta de los últimos 12 meses dividida por el patrimonio (lo que le queda a los dueños después de pagar toda la deuda). A diferencia del ROA, el ROE sube si la empresa se endeuda más — un ROE alto no es automáticamente mejor solo por ser un número más grande.",
    campoMetricaAvanzada: "roe_pct",
  },
  {
    id: "roic",
    termino: "ROIC (aprox.)",
    definicion:
      "Operating income sobre el capital invertido (deuda + patrimonio − caja). Acá se calcula sin ajustar por impuestos — no hay un tag XBRL de impuestos pagados disponible para este cálculo — así que es una aproximación honesta, no el ROIC \"de libro\" con NOPAT. Compara cuánto genera el negocio por cada dólar realmente invertido en operarlo, venga de deuda o de dueños.",
    campoMetricaAvanzada: "roic_pct",
  },
  {
    id: "roce",
    termino: "ROCE",
    definicion:
      "Operating income sobre (activos totales menos pasivos corrientes). Mide algo parecido al ROIC pero con otro denominador (\"capital empleado\" en vez de \"capital invertido\") — que salga distinto al ROIC para la misma empresa es normal, no un error de cálculo.",
    campoMetricaAvanzada: "roce_pct",
  },
  {
    id: "pe",
    termino: "P/E (Price to Earnings)",
    definicion:
      "El precio de la acción dividido por su EPS de los últimos 12 meses. Dice cuántos años de la ganancia actual estás pagando por la acción al precio de hoy — un P/E de 30 significa pagar 30 años de utilidad actual, asumiendo (algo que casi nunca pasa) que esa utilidad no cambia.",
    campoMetricaAvanzada: "pe",
  },
  {
    id: "ev-ingresos",
    termino: "EV/Ingresos",
    definicion:
      "Enterprise value dividido por los ingresos de los últimos 12 meses. Se usa cuando una empresa todavía no tiene ganancia (o es muy chica) y el P/E no sirve — compara cuánto se paga por cada dólar de ventas, sin importar si esas ventas ya son rentables.",
    campoMetricaAvanzada: "ev_ingresos",
  },
  {
    id: "ev-ebitda",
    termino: "EV/EBITDA",
    definicion:
      "Enterprise value dividido por EBITDA. Cumple un rol parecido al P/E, pero usando EV en vez de market cap (compara empresas con distinta deuda en igualdad de condiciones) y EBITDA en vez de utilidad neta (no lo distorsionan diferencias de depreciación o impuestos entre empresas).",
    campoMetricaAvanzada: "ev_ebitda",
  },
  {
    id: "p-vl",
    termino: "P/Valor libro (P/VL)",
    definicion:
      "Market cap dividido por el patrimonio contable. Un P/VL de 1 significa que el mercado paga exactamente lo que dicen los libros que vale la empresa; sobre 1, el mercado le está poniendo precio a algo que no está en el balance (marca, tecnología, expectativas de crecimiento futuro).",
    campoMetricaAvanzada: "p_vl",
  },
  {
    id: "dividend-yield",
    termino: "Dividend yield",
    definicion:
      "Los dividendos pagados por acción en los últimos 12 meses, como porcentaje del precio de hoy. Es el retorno en efectivo que da la empresa solo por tener la acción, aparte de si el precio sube o baja.",
    campoMetricaAvanzada: "dividend_yield_pct",
  },
  {
    id: "payout-ratio",
    termino: "Payout ratio",
    definicion:
      "Qué porcentaje del EPS la empresa reparte como dividendo en vez de reinvertirlo en el negocio. Un payout sobre 100% significa que está pagando más dividendo del que gana — no es sostenible indefinidamente sin endeudarse o vender activos.",
    campoMetricaAvanzada: "payout_ratio_pct",
  },
  {
    id: "beta",
    termino: "Beta (propio, vs. VOO)",
    definicion:
      "Qué tan fuerte se mueve el precio de la acción comparado con el mercado (acá, VOO — el ETF del S&P 500), calculado por el propio proyecto vía regresión contra su histórico de precios, no comprado a un proveedor. Un beta de 1,5 significa que, históricamente, cuando VOO sube o baja 1%, esta acción se mueve alrededor de 1,5% en la misma dirección — más volátil que el mercado. Bajo 1, se mueve menos.",
    campoMetricaAvanzada: "beta",
  },
];
