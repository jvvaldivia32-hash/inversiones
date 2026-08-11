import { useEffect, useState } from "react";
import { calcularEstadoMercado } from "../lib/mercado";
import "./EstadoMercado.css";

export default function EstadoMercado() {
  const [abierto, setAbierto] = useState(() => calcularEstadoMercado().abierto);

  useEffect(() => {
    const id = setInterval(() => {
      setAbierto(calcularEstadoMercado().abierto);
    }, 60_000);
    return () => clearInterval(id);
  }, []);

  return (
    <span className={`estado-mercado ${abierto ? "estado-mercado--abierto" : "estado-mercado--cerrado"}`}>
      <span className="estado-mercado-punto" aria-hidden="true" />
      Wall Street {abierto ? "abierto" : "cerrado"}
    </span>
  );
}
