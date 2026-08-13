export default function CardInversionPendiente({ ticker }: { ticker: string }) {
  return (
    <article className="card-inversion card-inversion--pendiente">
      <h3 className="card-inversion-ticker">{ticker}</h3>
      <p>Agregado. Aparece en la próxima actualización — el recolector corre cada hora.</p>
    </article>
  );
}
