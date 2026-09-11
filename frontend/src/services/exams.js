import { apiRequest } from "./api";

export function getExams(signal) {
  return apiRequest("/exams", { signal });
}

export function createExam(exam) {
  return apiRequest("/exams", { method: "POST", body: exam });
}

export function updateExam(examId, exam) {
  return apiRequest(`/exams/${examId}`, { method: "PUT", body: exam });
}

export function deleteExam(examId) {
  return apiRequest(`/exams/${examId}`, { method: "DELETE" });
}
