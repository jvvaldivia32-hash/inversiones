import "./NavBar.css";

const PESTANAS = [
  { id: "mundo", etiqueta: "Mundo" },
  { id: "chile", etiqueta: "Chile" },
  { id: "actualidad", etiqueta: "Actualidad" },
  { id: "mis-inversiones", etiqueta: "Mis inversiones" },
  { id: "referencias", etiqueta: "Referencias" },
  { id: "radar", etiqueta: "Radar" },
];

function irA(id: string) {
  const destino = document.getElementById(id);
  if (!destino) return;
  const sinMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  destino.scrollIntoView({ block: "start", behavior: sinMovimiento ? "auto" : "smooth" });
}

export default function NavBar() {
  return (
    <nav className="nav-bar" aria-label="Navegación de secciones">
      {PESTANAS.map((p) => (
        <button key={p.id} type="button" onClick={() => irA(p.id)}>
          {p.etiqueta}
        </button>
      ))}
    </nav>
  );
}
