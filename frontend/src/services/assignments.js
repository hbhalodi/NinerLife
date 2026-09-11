import { apiRequest } from "./api";

export function getAssignments(signal) {
  return apiRequest("/assignments", { signal });
}

export function getAssignmentInsights(signal) {
  return apiRequest("/assignments/insights", { signal });
}

export function createAssignment(assignment) {
  return apiRequest("/assignments", { method: "POST", body: assignment });
}

export function updateAssignment(assignmentId, assignment) {
  return apiRequest(`/assignments/${assignmentId}`, {
    method: "PUT",
    body: assignment,
  });
}

export function deleteAssignment(assignmentId) {
  return apiRequest(`/assignments/${assignmentId}`, { method: "DELETE" });
}
