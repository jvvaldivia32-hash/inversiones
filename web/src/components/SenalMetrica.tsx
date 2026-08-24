import type { Lectura } from "../lib/referenciasMetricas";
import "./SenalMetrica.css";

// Punto de color + la lectura de referencia de una métrica. Deliberadamente por métrica y
// nada más: no existe (ni debe existir sin preguntarle a José primero) un puntaje que sume
// estos niveles en un veredicto de compra — ver el comentario largo en referenciasMetricas.ts
// y la regla dura del Radar en CLAUDE.md.
//
// "neutro" no pinta color: la regla de diseño del proyecto es que el color es solo señal, y
// "está en el rango normal" no es una señal, es la ausencia de una.
const ETIQUETA_NIVEL: Record<Lectura["nivel"], string> = {
  bueno: "buena señal",
  neutro: "en el rango normal",
  atencion: "para mirar con calma",
  malo: "mala señal",
};

export default function SenalMetrica({ lectura }: { lectura: Lectura }) {
  return (
    <span className={`senal senal--${lectura.nivel}`}>
      <span className="senal-punto" aria-hidden="true" />
      <span className="senal-nivel-lectores">{ETIQUETA_NIVEL[lectura.nivel]}: </span>
      {lectura.texto}
    </span>
  );
}
