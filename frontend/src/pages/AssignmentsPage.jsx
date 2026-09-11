import { useEffect, useState } from "react";

import Notice from "../components/Notice";
import ResourceHeader from "../components/ResourceHeader";
import { EmptyState, LoadingState } from "../components/ResourceStates";
import { getErrorMessage } from "../services/api";
import {
  createAssignment,
  deleteAssignment,
  getAssignments,
  updateAssignment,
} from "../services/assignments";
import { getCourses } from "../services/courses";

const emptyAssignmentForm = {
  name: "",
  course_id: "",
  due: "",
  difficulty: "Medium",
  estimated_hours: "",
  completed: false,
};

function formatDate(value) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}

export default function AssignmentsPage() {
  const [assignments, setAssignments] = useState([]);
  const [courses, setCourses] = useState([]);
  const [formData, setFormData] = useState(emptyAssignmentForm);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    const requestController = new AbortController();

    Promise.all([
      getAssignments(requestController.signal),
      getCourses(requestController.signal),
    ])
      .then(([assignmentData, courseData]) => {
        setAssignments(assignmentData);
        setCourses(courseData);
      })
      .catch((error) => {
        if (error.name !== "AbortError") {
          setErrorMessage(
            getErrorMessage(error, "Assignments could not be loaded right now."),
          );
        }
      })
      .finally(() => setLoading(false));

    return () => requestController.abort();
  }, []);

  const courseNames = new Map(
    courses.map((course) => [course.id, `${course.code} — ${course.name}`]),
  );

  async function refreshData() {
    const [assignmentData, courseData] = await Promise.all([
      getAssignments(),
      getCourses(),
    ]);
    setAssignments(assignmentData);
    setCourses(courseData);
  }

  function resetForm() {
    setFormData(emptyAssignmentForm);
    setEditingId(null);
  }

  function startEditing(assignment) {
    setFormData({
      name: assignment.name,
      course_id: String(assignment.course_id),
      due: assignment.due,
      difficulty: assignment.difficulty,
      estimated_hours: String(assignment.estimated_hours),
      completed: assignment.completed,
    });
    setEditingId(assignment.id);
    setErrorMessage("");
    setSuccessMessage("");
  }

  function updateFormField(event) {
    const { name, type, value, checked } = event.target;
    setFormData((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const estimatedHours = Number(formData.estimated_hours);

    setErrorMessage("");
    setSuccessMessage("");

    if (!formData.name.trim()) {
      setErrorMessage("Assignment name is required.");
      return;
    }

    if (!formData.course_id || !formData.due) {
      setErrorMessage("Choose a course and due date.");
      return;
    }

    if (!Number.isFinite(estimatedHours) || estimatedHours < 0) {
      setErrorMessage("Estimated hours must be zero or greater.");
      return;
    }

    const payload = {
      name: formData.name.trim(),
      course_id: Number(formData.course_id),
      due: formData.due,
      difficulty: formData.difficulty,
      estimated_hours: estimatedHours,
      completed: formData.completed,
    };

    setSubmitting(true);

    try {
      if (editingId === null) {
        await createAssignment(payload);
        setSuccessMessage(`${payload.name} was added.`);
      } else {
        await updateAssignment(editingId, payload);
        setSuccessMessage(`${payload.name} was updated.`);
      }

      resetForm();
      await refreshData();
    } catch (error) {
      setErrorMessage(
        getErrorMessage(error, "The assignment could not be saved right now."),
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(assignment) {
    const confirmed = window.confirm(
      `Delete ${assignment.name}? This cannot be undone.`,
    );

    if (!confirmed) {
      return;
    }

    setDeletingId(assignment.id);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      await deleteAssignment(assignment.id);
      if (editingId === assignment.id) {
        resetForm();
      }
      await refreshData();
      setSuccessMessage(`${assignment.name} was deleted.`);
    } catch (error) {
      setErrorMessage(
        getErrorMessage(error, "The assignment could not be deleted right now."),
      );
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="page-stack" aria-labelledby="assignments-title">
      <ResourceHeader
        eyebrow="Academic work"
        title="Assignments"
        description="Plan coursework, deadlines, and completion in one place."
        count={assignments.length}
        singularLabel="assignment"
        titleId="assignments-title"
      />

      <Notice type="error" message={errorMessage} />
      <Notice type="success" message={successMessage} />

      <div className="resource-workspace resource-workspace-wide-form">
        <section className="resource-form-panel" aria-labelledby="assignment-form-title">
          <div className="panel-heading">
            <p className="page-eyebrow">{editingId === null ? "Add new" : "Editing"}</p>
            <h2 id="assignment-form-title">
              {editingId === null ? "Add an assignment" : "Update assignment"}
            </h2>
            <p>Capture the work, due date, and expected effort.</p>
          </div>

          {courses.length === 0 && !loading && (
            <Notice
              type="error"
              message="Add a course before creating an assignment."
            />
          )}

          <form className="resource-form" onSubmit={handleSubmit}>
            <label className="form-field form-field-full">
              <span>Assignment name</span>
              <input
                name="name"
                value={formData.name}
                onChange={updateFormField}
                placeholder="Research outline"
                autoComplete="off"
                required
              />
            </label>

            <label className="form-field form-field-full">
              <span>Course</span>
              <select
                name="course_id"
                value={formData.course_id}
                onChange={updateFormField}
                required
              >
                <option value="">Select a course</option>
                {courses.map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.code} — {course.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-field">
              <span>Due date</span>
              <input
                name="due"
                type="date"
                value={formData.due}
                onChange={updateFormField}
                required
              />
            </label>

            <label className="form-field">
              <span>Difficulty</span>
              <select
                name="difficulty"
                value={formData.difficulty}
                onChange={updateFormField}
                required
              >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
              </select>
            </label>

            <label className="form-field form-field-full">
              <span>Estimated hours</span>
              <input
                name="estimated_hours"
                type="number"
                min="0"
                step="0.25"
                value={formData.estimated_hours}
                onChange={updateFormField}
                placeholder="3"
                required
              />
            </label>

            <label className="checkbox-field form-field-full">
              <input
                name="completed"
                type="checkbox"
                checked={formData.completed}
                onChange={updateFormField}
              />
              <span>Completed</span>
            </label>

            <div className="form-actions form-field-full">
              <button
                className="button button-primary"
                disabled={submitting || courses.length === 0}
                type="submit"
              >
                {submitting
                  ? "Saving…"
                  : editingId === null
                    ? "Add assignment"
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

        <section className="resource-list-panel" aria-labelledby="assignment-list-title">
          <div className="list-heading">
            <div>
              <p className="page-eyebrow">Coursework</p>
              <h2 id="assignment-list-title">All assignments</h2>
            </div>
            <span>{assignments.length} total</span>
          </div>

          {loading ? (
            <LoadingState label="assignments" />
          ) : assignments.length === 0 ? (
            <EmptyState
              mark="A"
              title="No assignments yet"
              message="Add your first assignment when you are ready to plan coursework."
            />
          ) : (
            <div className="resource-card-list">
              {assignments.map((assignment) => (
                <article className="resource-card record-card" key={assignment.id}>
                  <div className="record-card-heading">
                    <div>
                      <p className="record-context">
                        {courseNames.get(assignment.course_id) ??
                          `Course #${assignment.course_id}`}
                      </p>
                      <h3>{assignment.name}</h3>
                    </div>
                    <span
                      className={`completion-badge ${
                        assignment.completed ? "is-complete" : ""
                      }`}
                    >
                      {assignment.completed ? "Completed" : "Open"}
                    </span>
                  </div>

                  <dl className="record-details">
                    <div>
                      <dt>Due</dt>
                      <dd>{formatDate(assignment.due)}</dd>
                    </div>
                    <div>
                      <dt>Difficulty</dt>
                      <dd>
                        <span className={`difficulty difficulty-${assignment.difficulty.toLowerCase()}`}>
                          {assignment.difficulty}
                        </span>
                      </dd>
                    </div>
                    <div>
                      <dt>Estimate</dt>
                      <dd>{assignment.estimated_hours} hours</dd>
                    </div>
                  </dl>

                  <div className="record-actions">
                    <button
                      className="button button-secondary button-small"
                      type="button"
                      onClick={() => startEditing(assignment)}
                    >
                      Edit
                    </button>
                    <button
                      className="button button-danger button-small"
                      type="button"
                      onClick={() => handleDelete(assignment)}
                      disabled={deletingId === assignment.id}
                    >
                      {deletingId === assignment.id ? "Deleting…" : "Delete"}
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
