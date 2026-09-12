import { useEffect, useState } from "react";

import Notice from "../components/Notice";
import ResourceHeader from "../components/ResourceHeader";
import { EmptyState, LoadingState } from "../components/ResourceStates";
import { getErrorMessage } from "../services/api";
import {
  createCourse,
  deleteCourse,
  getCourses,
  updateCourse,
} from "../services/courses";

const emptyCourseForm = {
  code: "",
  name: "",
};

export default function CoursesPage() {
  const [courses, setCourses] = useState([]);
  const [formData, setFormData] = useState(emptyCourseForm);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    const requestController = new AbortController();

    getCourses(requestController.signal)
      .then(setCourses)
      .catch((error) => {
        if (error.name !== "AbortError") {
          setErrorMessage(
            getErrorMessage(error, "Courses could not be loaded right now."),
          );
        }
      })
      .finally(() => setLoading(false));

    return () => requestController.abort();
  }, []);

  async function refreshCourses() {
    setCourses(await getCourses());
  }

  function resetForm() {
    setFormData(emptyCourseForm);
    setEditingId(null);
  }

  function startEditing(course) {
    setFormData({ code: course.code, name: course.name });
    setEditingId(course.id);
    setErrorMessage("");
    setSuccessMessage("");
  }

  function updateFormField(event) {
    const { name, value } = event.target;
    setFormData((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const payload = {
      code: formData.code.trim(),
      name: formData.name.trim(),
    };

    setErrorMessage("");
    setSuccessMessage("");

    if (!payload.code || !payload.name) {
      setErrorMessage("Course code and name are both required.");
      return;
    }

    setSubmitting(true);

    try {
      if (editingId === null) {
        await createCourse(payload);
        setSuccessMessage(`${payload.code} was added.`);
      } else {
        await updateCourse(editingId, payload);
        setSuccessMessage(`${payload.code} was updated.`);
      }

      resetForm();
      await refreshCourses();
    } catch (error) {
      setErrorMessage(
        getErrorMessage(error, "The course could not be saved right now."),
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(course) {
    const confirmed = window.confirm(
      `Delete ${course.code} — ${course.name}? This cannot be undone.`,
    );

    if (!confirmed) {
      return;
    }

    setDeletingId(course.id);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      await deleteCourse(course.id);
      if (editingId === course.id) {
        resetForm();
      }
      await refreshCourses();
      setSuccessMessage(`${course.code} was deleted.`);
    } catch (error) {
      setErrorMessage(
        getErrorMessage(error, "The course could not be deleted right now."),
      );
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="page-stack" aria-labelledby="courses-title">
      <ResourceHeader
        eyebrow="Your semester"
        title="Courses"
        description="Manage the classes that connect your assignments and exams."
        count={courses.length}
        singularLabel="course"
        titleId="courses-title"
      />

      <Notice type="error" message={errorMessage} />
      <Notice type="success" message={successMessage} />

      <div className="resource-workspace">
        <section
          className="resource-form-panel"
          aria-labelledby="course-form-title"
          aria-busy={submitting}
        >
          <div className="panel-heading">
            <p className="page-eyebrow">{editingId === null ? "Add new" : "Editing"}</p>
            <h2 id="course-form-title">
              {editingId === null ? "Add a course" : "Update course"}
            </h2>
            <p>Use the code shown on your syllabus or course schedule.</p>
          </div>

          <form className="resource-form" onSubmit={handleSubmit}>
            <label className="form-field">
              <span>Course code</span>
              <input
                name="code"
                value={formData.code}
                onChange={updateFormField}
                placeholder="ITSC 3155"
                autoComplete="off"
                required
              />
            </label>

            <label className="form-field">
              <span>Course name</span>
              <input
                name="name"
                value={formData.name}
                onChange={updateFormField}
                placeholder="Software Engineering"
                autoComplete="off"
                required
              />
            </label>

            <div className="form-actions">
              <button className="button button-primary" disabled={submitting} type="submit">
                {submitting
                  ? "Saving…"
                  : editingId === null
                    ? "Add course"
                    : "Save changes"}
              </button>
              {editingId !== null && (
                <button
                  className="button button-quiet"
                  type="button"
                  onClick={resetForm}
                  disabled={submitting}
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        </section>

        <section className="resource-list-panel" aria-labelledby="course-list-title">
          <div className="list-heading">
            <div>
              <p className="page-eyebrow">Current schedule</p>
              <h2 id="course-list-title">Your courses</h2>
            </div>
            <span>{courses.length} total</span>
          </div>

          {loading ? (
            <LoadingState label="courses" />
          ) : courses.length === 0 ? (
            <EmptyState
              mark="C"
              title="No courses yet"
              message="Add your first course to start organizing assignments and exams."
            />
          ) : (
            <div className="resource-card-list">
              {courses.map((course) => (
                <article className="resource-card course-card" key={course.id}>
                  <div className="record-main">
                    <span className="course-code">{course.code}</span>
                    <h3>{course.name}</h3>
                  </div>
                  <div className="record-actions">
                    <button
                      className="button button-secondary button-small"
                      type="button"
                      onClick={() => startEditing(course)}
                      aria-label={`Edit ${course.code} — ${course.name}`}
                    >
                      Edit
                    </button>
                    <button
                      className="button button-danger button-small"
                      type="button"
                      onClick={() => handleDelete(course)}
                      disabled={deletingId === course.id}
                      aria-label={`Delete ${course.code} — ${course.name}`}
                    >
                      {deletingId === course.id ? "Deleting…" : "Delete"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
