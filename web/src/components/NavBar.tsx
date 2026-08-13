import type { Vista } from "../lib/navegacion";
import "./NavBar.css";

const SECCIONES_DIA = [
  { id: "referencias", etiqueta: "Referencias" },
  { id: "mundo", etiqueta: "Mundo" },
  { id: "chile", etiqueta: "Chile" },
  { id: "actualidad", etiqueta: "Actualidad" },
];

const SECCIONES_INVERSION = [
  { id: "mis-inversiones", etiqueta: "Mis inversiones" },
  { id: "radar", etiqueta: "Radar" },
];

const SECCIONES_POR_VISTA: Record<Vista, { id: string; etiqueta: string }[]> = {
  dia: SECCIONES_DIA,
  inversion: SECCIONES_INVERSION,
  diccionario: [],
};

interface NavBarProps {
  vista: Vista;
  onIrA: (id: string) => void;
}

export default function NavBar({ vista, onIrA }: NavBarProps) {
  const secciones = SECCIONES_POR_VISTA[vista];

  return (
    <nav className="nav-bar" aria-label="Navegación">
      <div className="nav-bar-tabs" role="tablist" aria-label="Vista">
        <button
          type="button"
          role="tab"
          aria-selected={vista === "dia"}
          className={vista === "dia" ? "activo" : ""}
          onClick={() => onIrA("referencias")}
        >
          Hoy
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={vista === "inversion"}
          className={vista === "inversion" ? "activo" : ""}
          onClick={() => onIrA("mis-inversiones")}
        >
          Inversión
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={vista === "diccionario"}
          className={vista === "diccionario" ? "activo" : ""}
          onClick={() => onIrA("diccionario")}
        >
          Diccionario
        </button>
      </div>

      {secciones.length > 0 && (
        <>
          <span className="nav-bar-divisor" aria-hidden="true" />
          <div className="nav-bar-secciones">
            {secciones.map((s) => (
              <button key={s.id} type="button" onClick={() => onIrA(s.id)}>
                {s.etiqueta}
              </button>
            ))}
          </div>
        </>
      )}
    </nav>
  );
}
