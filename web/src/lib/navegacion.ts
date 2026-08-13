export type Vista = "dia" | "inversion" | "diccionario";

export const SECCION_A_VISTA: Record<string, Vista> = {
  referencias: "dia",
  mundo: "dia",
  chile: "dia",
  actualidad: "dia",
  "mis-inversiones": "inversion",
  radar: "inversion",
  diccionario: "diccionario",
};
