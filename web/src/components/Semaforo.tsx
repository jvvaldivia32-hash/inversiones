import type { EstadoSemaforo } from "../types";
import "./Semaforo.css";

const ETIQUETA: Record<EstadoSemaforo, string> = {
  verde: "Tesis intacta",
  ambar: "Revisar",
  rojo: "Tesis rota",
};

export default function Semaforo({ estado }: { estado: EstadoSemaforo }) {
  return (
    <span className={`semaforo semaforo--${estado}`}>
      <span className="semaforo-punto" aria-hidden="true" />
      {ETIQUETA[estado]}
    </span>
  );
}
