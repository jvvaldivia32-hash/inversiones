import type { ItemActualidad } from "../types";
import "./Actualidad.css";

export default function Actualidad({ items }: { items: ItemActualidad[] }) {
  return (
    <ul className="actualidad">
      {items.slice(0, 5).map((item) => (
        <li key={item.url}>
          <a href={item.url} target="_blank" rel="noreferrer">
            {item.titular}
          </a>
          <span className="actualidad-medio">[{item.medio}]</span>
        </li>
      ))}
    </ul>
  );
}
