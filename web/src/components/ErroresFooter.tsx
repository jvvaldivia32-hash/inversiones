import "./ErroresFooter.css";

export default function ErroresFooter({ errores }: { errores: string[] }) {
  if (errores.length === 0) return null;

  return (
    <footer className="errores-footer">
      {errores.map((e) => (
        <p key={e}>· {e}</p>
      ))}
    </footer>
  );
}
