export function formatUSD(valor: number): string {
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(valor);
}

export function formatNumeroCL(valor: number, decimales = 2): string {
  return new Intl.NumberFormat("es-CL", {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  }).format(valor);
}

export function formatPct(valor: number, decimales = 1): string {
  const signo = valor > 0 ? "+" : "";
  return `${signo}${formatNumeroCL(valor, decimales)}%`;
}

export function formatFechaCorta(iso: string): string {
  return new Intl.DateTimeFormat("es-CL", { day: "2-digit", month: "short" }).format(
    new Date(iso),
  );
}

// En el rango de 5 años, "día-mes" es ambiguo — los meses se repiten cada año y no hay
// forma de saber a cuál corresponde cada punto. Ahí el eje muestra el año directamente.
export function formatFechaEje(iso: string, esRangoLargo: boolean): string {
  if (esRangoLargo) {
    return new Intl.DateTimeFormat("es-CL", { year: "numeric" }).format(new Date(iso));
  }
  return formatFechaCorta(iso);
}

export function formatFechaTooltip(iso: string, esRangoLargo: boolean): string {
  if (esRangoLargo) {
    return new Intl.DateTimeFormat("es-CL", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(iso));
  }
  return formatFechaCorta(iso);
}

export function formatHora(iso: string): string {
  return new Intl.DateTimeFormat("es-CL", { hour: "2-digit", minute: "2-digit" }).format(
    new Date(iso),
  );
}

export function formatMusd(valorMillones: number): string {
  return `US$${formatNumeroCL(valorMillones, 0)}M`;
}
