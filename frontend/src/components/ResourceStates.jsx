export function LoadingState({ label }) {
  return (
    <div className="resource-state" role="status" aria-live="polite" aria-busy="true">
      <span className="loading-mark" aria-hidden="true" />
      <p>Loading {label}…</p>
    </div>
  );
}

export function EmptyState({ mark, title, message }) {
  return (
    <div className="resource-state resource-state-empty" role="status">
      <span className="empty-panel-mark" aria-hidden="true">
        {mark}
      </span>
      <div>
        <h2>{title}</h2>
        <p>{message}</p>
      </div>
    </div>
  );
}
