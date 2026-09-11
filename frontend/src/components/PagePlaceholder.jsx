export default function PagePlaceholder({ eyebrow, title, description }) {
  return (
    <section className="page-stack" aria-labelledby="page-title">
      <div className="page-heading">
        <p className="page-eyebrow">{eyebrow}</p>
        <h1 id="page-title">{title}</h1>
        <p>{description}</p>
      </div>

      <div className="empty-panel">
        <span className="empty-panel-mark" aria-hidden="true">
          {title.slice(0, 1)}
        </span>
        <div>
          <h2>{title} foundation</h2>
          <p>Tools and data for this page will be added in a later phase.</p>
        </div>
      </div>
    </section>
  );
}
