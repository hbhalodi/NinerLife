const configuredApiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
const apiBaseUrl = configuredApiUrl.replace(/\/$/, "");

function formatApiDetail(detail, status) {
  if (status >= 500) {
    return "The server could not complete the request. Please try again shortly.";
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((issue) => {
        const field = issue.loc?.at(-1) ?? "request";
        return `${field}: ${issue.msg}`;
      })
      .join(" ");
  }

  return "The server could not complete the request.";
}

export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export async function apiRequest(
  path,
  { method = "GET", body, signal } = {},
) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    let responseBody;

    try {
      responseBody = await response.json();
    } catch {
      responseBody = null;
    }

    const detail = responseBody?.detail;
    throw new ApiError(
      formatApiDetail(detail, response.status),
      response.status,
      detail,
    );
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export function getErrorMessage(error, fallbackMessage) {
  if (error instanceof ApiError) {
    return error.message;
  }

  return fallbackMessage;
}

export function getHealth(signal) {
  return apiRequest("/health", { signal });
}
