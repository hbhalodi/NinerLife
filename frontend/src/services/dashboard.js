import { apiRequest } from "./api";

export function getDashboardSummary({ workHours, signal } = {}) {
  const search = new URLSearchParams();

  if (workHours !== undefined) {
    search.set("work_hours", String(workHours));
  }

  const query = search.toString();
  return apiRequest(`/dashboard/summary${query ? `?${query}` : ""}`, {
    signal,
  });
}
