import { useEffect, useState } from "react";

import { getHealth } from "../services/api";

export default function BackendStatus() {
  const [connectionStatus, setConnectionStatus] = useState("checking");

  useEffect(() => {
    const requestController = new AbortController();

    getHealth(requestController.signal)
      .then(() => setConnectionStatus("connected"))
      .catch((error) => {
        if (error.name !== "AbortError") {
          setConnectionStatus("unavailable");
        }
      });

    return () => requestController.abort();
  }, []);

  const statusLabel = {
    checking: "Checking backend",
    connected: "Backend: Connected",
    unavailable: "Backend: Unavailable",
  }[connectionStatus];

  return (
    <div
      className={`backend-status backend-status-${connectionStatus}`}
      role="status"
      aria-live="polite"
    >
      <span className="status-indicator" aria-hidden="true" />
      {statusLabel}
    </div>
  );
}
