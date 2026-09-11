import { apiRequest } from "./api";

export function getCourses(signal) {
  return apiRequest("/courses", { signal });
}

export function createCourse(course) {
  return apiRequest("/courses", { method: "POST", body: course });
}

export function updateCourse(courseId, course) {
  return apiRequest(`/courses/${courseId}`, { method: "PUT", body: course });
}

export function deleteCourse(courseId) {
  return apiRequest(`/courses/${courseId}`, { method: "DELETE" });
}
