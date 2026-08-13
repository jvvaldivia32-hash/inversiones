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

export type RangoPrecio = "1M" | "6M" | "YTD" | "1A" | "5A";

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
  };
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
}
