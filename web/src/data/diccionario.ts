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

export interface EntradaDiccionario {
  id: string;
  termino: string;
  definicion: string;
  campoEjemplo?: CampoFundamentalEjemplo;
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
];
