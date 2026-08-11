// Feriados NYSE 2026, fechas fijas (no calculadas por regla) — actualizar a mano cada año.
// No contempla cierres anticipados (víspera de Thanksgiving, Nochebuena).
const FERIADOS_NYSE = new Set([
  "2026-01-01", // Año Nuevo
  "2026-01-19", // Martin Luther King Jr. Day
  "2026-02-16", // Presidents' Day
  "2026-04-03", // Good Friday
  "2026-05-25", // Memorial Day
  "2026-06-19", // Juneteenth
  "2026-07-03", // Independence Day (observado, el 4 cae sábado)
  "2026-09-07", // Labor Day
  "2026-11-26", // Thanksgiving
  "2026-12-25", // Navidad
]);

export interface EstadoMercado {
  abierto: boolean;
}

export function calcularEstadoMercado(fecha: Date = new Date()): EstadoMercado {
  const partes = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    weekday: "short",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(fecha);

  const obtener = (tipo: string) => partes.find((p) => p.type === tipo)?.value ?? "";
  const diaSemana = obtener("weekday");
  const fechaISO = `${obtener("year")}-${obtener("month")}-${obtener("day")}`;
  const hora = Number(obtener("hour")) % 24; // Intl a veces da "24" para medianoche
  const minuto = Number(obtener("minute"));

  const esFinDeSemana = diaSemana === "Sat" || diaSemana === "Sun";
  const esFeriado = FERIADOS_NYSE.has(fechaISO);
  const minutosDelDia = hora * 60 + minuto;
  const dentroDeHorario = minutosDelDia >= 9 * 60 + 30 && minutosDelDia < 16 * 60;

  return { abierto: !esFinDeSemana && !esFeriado && dentroDeHorario };
}
