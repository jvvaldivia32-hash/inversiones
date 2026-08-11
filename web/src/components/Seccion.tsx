import type { ReactNode } from "react";
import "./Seccion.css";

interface SeccionProps {
  titulo: string;
  compacta?: boolean;
  children: ReactNode;
}

export default function Seccion({ titulo, compacta, children }: SeccionProps) {
  return (
    <section className={`seccion ${compacta ? "seccion--compacta" : ""}`}>
      <h2 className="seccion-titulo">{titulo}</h2>
      <div className="seccion-cuerpo">{children}</div>
    </section>
  );
}
