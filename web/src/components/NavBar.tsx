import type { Vista } from "../lib/navegacion";
import "./NavBar.css";

// `soloMovil`: a partir de 960px Actualidad es la columna izquierda sticky de la vista
// "Hoy" (ver .vista-hoy-sidebar en App.css) — está siempre a la vista, así que el atajo
// del nav no lleva a ningún lado que no se vea ya. En mobile las secciones se apilan y
// Actualidad queda al final de todo, ahí el atajo sí sirve. Pedido del usuario 2026-08-21.
const SECCIONES_DIA = [
  { id: "referencias", etiqueta: "Referencias" },
  { id: "mundo", etiqueta: "Mundo" },
  { id: "chile", etiqueta: "Chile" },
  { id: "actualidad", etiqueta: "Actualidad", soloMovil: true },
];

const SECCIONES_INVERSION = [
  { id: "fintual", etiqueta: "Mi portafolio" },
  { id: "mis-inversiones", etiqueta: "Mis inversiones" },
  { id: "radar", etiqueta: "Radar" },
];

type SeccionNav = { id: string; etiqueta: string; soloMovil?: boolean };

const SECCIONES_POR_VISTA: Record<Vista, SeccionNav[]> = {
  dia: SECCIONES_DIA,
  inversion: SECCIONES_INVERSION,
  diccionario: [],
  amigos: [],
  paper: [],
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
          aria-selected={vista === "paper"}
          className={vista === "paper" ? "activo" : ""}
          onClick={() => onIrA("paper-investing")}
        >
          Simulador
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
        <button
          type="button"
          role="tab"
          aria-selected={vista === "amigos"}
          className={vista === "amigos" ? "activo" : ""}
          onClick={() => onIrA("amigos")}
        >
          Otros
        </button>
      </div>

      {secciones.length > 0 && (
        <>
          <span className="nav-bar-divisor" aria-hidden="true" />
          <div className="nav-bar-secciones">
            {secciones.map((s) => (
              <button
                key={s.id}
                type="button"
                className={s.soloMovil ? "nav-bar-solo-movil" : undefined}
                onClick={() => onIrA(s.id)}
              >
                {s.etiqueta}
              </button>
            ))}
          </div>
        </>
      )}
    </nav>
  );
}
