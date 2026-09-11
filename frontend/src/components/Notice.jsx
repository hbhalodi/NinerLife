export default function Notice({ type = "error", message }) {
  if (!message) {
    return null;
  }

  return (
    <div
      className={`notice notice-${type}`}
      role={type === "error" ? "alert" : "status"}
    >
      {message}
    </div>
  );
}
