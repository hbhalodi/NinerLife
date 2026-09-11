import { apiRequest } from "./api";

export function getStudyPlan({ availableHours, horizonDays, signal } = {}) {
  const search = new URLSearchParams();

  if (availableHours !== undefined) {
    search.set("available_hours", String(availableHours));
  }
  if (horizonDays !== undefined) {
    search.set("horizon_days", String(horizonDays));
  }

  const query = search.toString();
  return apiRequest(`/study-plan${query ? `?${query}` : ""}`, { signal });
}
