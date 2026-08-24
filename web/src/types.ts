export interface Articulo {
  titular: string;
  extracto: string;
  medio: string;
  grupo: string;
  lean: string;
  url: string;
  fecha: string;
}

export interface Historia {
  titulo_neutral: string;
  resumen: string;
  articulos: Articulo[];
  leans_presentes: string[];
  grupos_presentes: string[];
  cobertura_unilateral: boolean;
}

export interface ItemActualidad {
  titular: string;
  medio: string;
  url: string;
  fecha: string;
}

export type RangoPrecio = "1M" | "6M" | "YTD" | "1A" | "5A" | "10A";

export interface PuntoPrecio {
  fecha: string;
  valor: number;
}

export type SeriePrecio = Record<RangoPrecio, PuntoPrecio[]>;

export interface PuntoFundamental {
  periodo: string;
  valor: number;
}

export interface Fundamentales {
  periodo: string;
  fuente_url: string;
  series: {
    ingresos_musd: PuntoFundamental[];
    op_income_musd: PuntoFundamental[];
    eps_gaap: PuntoFundamental[];
    eps_non_gaap: PuntoFundamental[];
    margen_operativo: PuntoFundamental[];
    capex_musd: PuntoFundamental[];
    flujo_op_musd: PuntoFundamental[];
    // Agregados para "métricas avanzadas" (extra fuera del plan madre, 2026-08-14) — el
    // insumo crudo de estas 4 series vive acá, los ratios calculados a partir de ellas
    // viven en MetricasAvanzadas.
    utilidad_neta_musd: PuntoFundamental[];
    utilidad_bruta_musd: PuntoFundamental[];
    dep_amortizacion_musd: PuntoFundamental[];
    dividendo_por_accion: PuntoFundamental[];
  };
}

// Ratios calculados (collector/sources/metricas_avanzadas.py) a partir de Fundamentales +
// balance EDGAR + precio + histórico — cada campo es independiente y puede venir en null
// si falta un insumo para calcularlo puntual (nunca se inventa un valor parcial).
export interface MetricasAvanzadas {
  market_cap_musd: number | null;
  enterprise_value_musd: number | null;
  deuda_neta_musd: number | null;
  deuda_neta_ebitda: number | null;
  // null también para bancos (mismo criterio que RadarCandidato.metricas.deuda_patrimonio,
  // sección 3.3 del plan madre) — no es una señal de salud en ese modelo de negocio.
  deuda_patrimonio: number | null;
  margen_bruto_pct: number | null;
  margen_ebit_pct: number | null;
  roa_pct: number | null;
  roe_pct: number | null;
  // Aproximado: EBIT / capital invertido, sin ajuste por tasa de impuesto (no hay tag
  // XBRL de impuestos pagados en este cálculo) — no es el ROIC "de libro" con NOPAT.
  roic_pct: number | null;
  roce_pct: number | null;
  pe: number | null;
  ev_ingresos: number | null;
  ev_ebitda: number | null;
  p_vl: number | null;
  dividend_yield_pct: number | null;
  payout_ratio_pct: number | null;
  maximo_52s: number | null;
  minimo_52s: number | null;
  // Calculado por nosotros vía regresión contra el histórico de VOO — no es el beta
  // "oficial" de un proveedor de datos.
  beta: number | null;
}

export interface Segmento {
  nombre: string;
  ingresos_musd?: number;
  var_pct: number;
  cita: string;
  detalle?: Segmento[];
}

export type EstadoSemaforo = "verde" | "ambar" | "rojo";

export interface LecturaTesis {
  periodo: string;
  fecha_reporte: string;
  valor: number;
  semaforo: EstadoSemaforo;
  fuente_url: string;
  cita_textual: string;
  extraido_por: "xbrl" | "segmento";
}

export type EstadoTesis = "activa" | "cumplida" | "rota" | "cerrada";

export interface Tesis {
  id: string;
  ticker: string;
  texto: string;
  metrica_campo: string;
  metrica_tipo: "fundamental" | "segmento";
  umbral_verde: number;
  umbral_rojo: number;
  direccion: "mayor_es_mejor" | "menor_es_mejor";
  fecha_escrita: string;
  estado: EstadoTesis;
  notas_cierre?: string;
  lecturas: LecturaTesis[];
}

export interface Posicion {
  ticker: string;
  nombre: string;
  precio: number;
  var_dia_pct: number;
  serie_precio: SeriePrecio;
  // Todo lo de acá abajo llega en fases posteriores (fundamentales en Fase 4, tesis en
  // Fase 7, noticias en Fase 2/3) — hasta entonces la card solo tiene precio real.
  var_ano_pct?: number;
  proxima_earnings?: string;
  fundamentales?: Fundamentales;
  metricas_avanzadas?: MetricasAvanzadas;
  segmentos?: Segmento[];
  // URL del 8-K/press release del que salieron las citas de `segmentos` — distinto del
  // 10-Q/10-K de `fundamentales`, son filings diferentes.
  segmentos_fuente_url?: string;
  // Puede haber varias tesis por ticker: una vieja cerrada y una nueva activa conviven —
  // "editar" una tesis siempre es cerrar la anterior y crear otra, nunca modificar in situ.
  tesis?: Tesis[];
  noticias?: Articulo[];
}

export interface IndiceReferencia {
  ticker: string;
  nombre: string;
  precio: number;
  var_dia_pct: number;
}

export interface ReferenciasChile {
  ipsa: number;
  uf: number;
  dolar: number;
  tpm: number;
  ipc_12m: number;
  fuente: string;
}

export interface Referencias {
  indices: IndiceReferencia[];
  chile: ReferenciasChile;
}

// Simulador de cartera ficticia ("paper investing", extra 2026-08-20) — mismo modelo que
// mi-inversion (acciones + costo base, nunca el monto/% crudo), más un saldo de efectivo
// del que salen las compras y al que vuelven las ventas.
export interface PaperInvestingAporte {
  fecha: string;
  monto_usd: number;
}

export interface PaperInvestingPosicion {
  acciones: number;
  costo_base_usd: number;
}

export interface PaperInvestingResumen {
  fecha_inicio: string;
  saldo_no_invertido_usd: number;
  aportes: PaperInvestingAporte[];
  posiciones: Record<string, PaperInvestingPosicion>;
}

export interface RadarCandidato {
  ticker: string;
  nombre: string;
  pct_bajo_maximo: number;
  motivo: string;
  metricas: {
    ingresos_var_pct: number;
    margen_op: number;
    // null para bancos — deuda/patrimonio no es una señal de salud en ese modelo de
    // negocio, sección 3.3 del plan madre.
    deuda_patrimonio: number | null;
  };
  serie_precio: SeriePrecio;
}

export interface RadarDescartado {
  ticker: string;
  pct_bajo_maximo: number;
  motivo_descarte: string;
}

export interface RadarData {
  candidatos: RadarCandidato[];
  descartados: RadarDescartado[];
  ultima_corrida: string;
}

export interface FintualGoal {
  id: string;
  nombre: string;
  saldo: number;
}

export interface Fintual {
  goals: FintualGoal[];
  saldo_total: number;
  actualizado: string;
}

export interface AmigoTitular {
  titular: string;
  medio: string;
  url: string;
}

export interface AmigoSeguimiento {
  tipo: "ticker" | "palabra_clave";
  valor: string;
  // Forma de `datos` depende de `tipo`: ticker -> {precio, var_dia_pct}, palabra_clave ->
  // {titulares}. Puede venir null si nunca se pudo resolver (ticker roto la primera vez).
  datos: { precio?: number; var_dia_pct?: number; titulares?: AmigoTitular[] } | null;
}

export interface Amigo {
  id: string;
  nombre: string;
  // Gate de contraseña, chequeado en el cliente contra este valor tal cual llega en
  // daily.json (público) — a propósito no es un secreto real, solo evita que Amigo 1 y
  // Amigo 2 se confundan editando la tarjeta equivocada. Ver Amigos.tsx.
  clave?: string;
  seguimientos: AmigoSeguimiento[];
  actualizado?: string;
}

export interface DailyData {
  generado: string;
  errores: string[];
  bloques: {
    mundo: Historia[];
    chile: Historia[];
    actualidad: ItemActualidad[];
  };
  posiciones: Posicion[];
  referencias: Referencias;
  radar: RadarData;
  // Portafolio real de Fintual — opcional porque solo existe una vez que corra
  // fintual_diario.py al menos una vez; sin rentabilidad a propósito, la API no la
  // expone (solo saldo actual, "nav", por meta de inversión).
  fintual?: Fintual;
  // Sección "Amigos" — extra fuera del plan madre (2026-08-14). Opcional por lo mismo:
  // solo existe una vez que corra amigos_diario.py al menos una vez.
  amigos?: Amigo[];
}
