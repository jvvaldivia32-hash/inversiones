export default function CardInversionPendiente({ ticker }: { ticker: string }) {
  return (
    <article className="card-inversion card-inversion--pendiente">
      <h3 className="card-inversion-ticker">{ticker}</h3>
      <p>Agregado. Aparece en el próximo briefing (mañana 07:00).</p>
    </article>
  );
}
