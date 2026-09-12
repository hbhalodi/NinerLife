export default function Notice({ type = "error", message }) {
  if (!message) {
    return null;
  }

  return (
    <div
      className={`notice notice-${type}`}
      role={type === "error" ? "alert" : "status"}
      aria-atomic="true"
      aria-live={type === "error" ? "assertive" : "polite"}
    >
      <strong className="notice-label">
        {type === "error" ? "Action needed:" : "Saved:"}
      </strong>
      <span>{message}</span>
    </div>
  );
}
