export default function ResourceHeader({
  eyebrow,
  title,
  description,
  count,
  singularLabel,
  titleId,
}) {
  const countLabel = count === 1 ? singularLabel : `${singularLabel}s`;

  return (
    <div className="resource-page-heading">
      <div>
        <p className="page-eyebrow">{eyebrow}</p>
        <h1 id={titleId}>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="resource-count" aria-label={`${count} ${countLabel}`}>
        <strong>{count}</strong>
        <span>{countLabel}</span>
      </div>
    </div>
  );
}
