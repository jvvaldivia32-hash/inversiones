import { useState, type FormEvent } from "react";
import "./FormularioTesis.css";

interface FormularioTesisProps {
  ticker: string;
  metricasFundamental: string[];
  metricasSegmento: string[];
  onCreada: () => void;
}

export default function FormularioTesis({
  ticker,
  metricasFundamental,
  metricasSegmento,
  onCreada,
}: FormularioTesisProps) {
  const [abierto, setAbierto] = useState(false);
  const [texto, setTexto] = useState("");
  const [metrica, setMetrica] = useState("");
  const [umbralVerde, setUmbralVerde] = useState("");
  const [umbralRojo, setUmbralRojo] = useState("");
  const [direccion, setDireccion] = useState<"mayor_es_mejor" | "menor_es_mejor">("mayor_es_mejor");
  const [clave, setClave] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guardada, setGuardada] = useState(false);

  if (!abierto) {
    return (
      <button type="button" className="tesis-formulario-abrir" onClick={() => setAbierto(true)}>
        + escribir tesis nueva
      </button>
    );
  }

  if (guardada) {
    return (
      <p className="tesis-formulario-ok">
        Tesis guardada. Aparece en la próxima actualización del sitio (el collector corre
        cada hora), no al instante.
      </p>
    );
  }

  async function enviar(e: FormEvent) {
    e.preventDefault();
    const [metricaTipo, ...resto] = metrica.split(":");
    const metricaCampo = resto.join(":");
    if (!metricaTipo || !metricaCampo) {
      setError("elegí una métrica");
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      const resp = await fetch("/api/tesis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          accion: "crear",
          clave,
          ticker,
          texto,
          metrica_tipo: metricaTipo,
          metrica_campo: metricaCampo,
          umbral_verde: Number(umbralVerde),
          umbral_rojo: Number(umbralRojo),
          direccion,
        }),
      });
      const data = (await resp.json()) as { error?: string };
      if (!resp.ok) {
        setError(data.error ?? "no se pudo guardar");
        return;
      }
      setGuardada(true);
      onCreada();
    } catch {
      setError("no se pudo conectar");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="tesis-formulario" onSubmit={enviar}>
      <label>
        Tesis (qué creés que va a pasar en el negocio, no en el precio)
        <textarea
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          minLength={20}
          required
          rows={3}
        />
      </label>
      <label>
        Métrica
        <select value={metrica} onChange={(e) => setMetrica(e.target.value)} required>
          <option value="">elegir...</option>
          {metricasFundamental.map((campo) => (
            <option key={`fundamental:${campo}`} value={`fundamental:${campo}`}>
              {campo}
            </option>
          ))}
          {metricasSegmento.map((nombre) => (
            <option key={`segmento:${nombre}`} value={`segmento:${nombre}`}>
              {nombre}
            </option>
          ))}
        </select>
      </label>
      <label>
        Dirección
        <select
          value={direccion}
          onChange={(e) => setDireccion(e.target.value as "mayor_es_mejor" | "menor_es_mejor")}
        >
          <option value="mayor_es_mejor">mayor es mejor</option>
          <option value="menor_es_mejor">menor es mejor</option>
        </select>
      </label>
      <label>
        Umbral verde
        <input type="number" step="any" value={umbralVerde} onChange={(e) => setUmbralVerde(e.target.value)} required />
      </label>
      <label>
        Umbral rojo
        <input type="number" step="any" value={umbralRojo} onChange={(e) => setUmbralRojo(e.target.value)} required />
      </label>
      <label>
        Clave
        <input type="password" value={clave} onChange={(e) => setClave(e.target.value)} required />
      </label>
      {error && <p className="tesis-formulario-error">{error}</p>}
      <div className="tesis-formulario-botones">
        <button type="submit" disabled={enviando}>
          Guardar
        </button>
        <button type="button" onClick={() => setAbierto(false)} disabled={enviando}>
          Cancelar
        </button>
      </div>
    </form>
  );
}
