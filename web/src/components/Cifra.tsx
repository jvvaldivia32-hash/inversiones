import { useState } from "react";
import "./Cifra.css";

interface CifraProps {
  valor: React.ReactNode;
  fuente?: string;
  cita?: string;
  url?: string;
}

export default function Cifra({ valor, fuente, cita, url }: CifraProps) {
  const [abierta, setAbierta] = useState(false);

  if (!fuente) {
    return (
      <span className="cifra cifra--sin-verificar" title="Dato sin fuente verificada">
        {valor}
        <sup>sin verificar</sup>
      </span>
    );
  }

  return (
    <span className="cifra-wrap">
      <button
        type="button"
        className="cifra cifra--con-fuente"
        aria-expanded={abierta}
        onClick={() => setAbierta((v) => !v)}
      >
        {valor}
      </button>
      {abierta && (
        <span className="cifra-popover" role="note">
          {cita && <span className="cifra-cita">&ldquo;{cita}&rdquo;</span>}
          <span className="cifra-fuente">
            {url ? (
              <a href={url} target="_blank" rel="noreferrer">
                {fuente} ↗
              </a>
            ) : (
              fuente
            )}
          </span>
        </span>
      )}
    </span>
  );
}
