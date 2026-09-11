const configuredApiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
const apiBaseUrl = configuredApiUrl.replace(/\/$/, "");

export async function getHealth(signal) {
  const response = await fetch(`${apiBaseUrl}/health`, { signal });

  if (!response.ok) {
    throw new Error(`Backend health check failed with status ${response.status}.`);
  }

  return response.json();
}
