import { useEffect, useState } from "react";

import Notice from "../components/Notice";
import ResourceHeader from "../components/ResourceHeader";
import { EmptyState, LoadingState } from "../components/ResourceStates";
import { getErrorMessage } from "../services/api";
import {
  createAssignment,
  deleteAssignment,
  getAssignmentInsights,
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

function getPastAssignments(assignments) {
  return assignments
    .filter((assignment) => assignment.completed)
    .sort(
      (first, second) =>
        second.due.localeCompare(first.due) || second.id - first.id,
    );
}

function AssignmentCard({
  assignment,
  deleting,
  completionPending,
  onDelete,
  onEdit,
  onSetCompletion,
}) {
  const isCompleted = assignment.completed;

  return (
    <article className="resource-card record-card">
      <div className="record-card-heading">
        <div>
          <p className="record-context">
            {assignment.course.code} — {assignment.course.name}
          </p>
          <h3>{assignment.name}</h3>
        </div>
        <span className={`completion-badge ${isCompleted ? "is-complete" : ""}`}>
          {isCompleted ? "Completed" : "Open"}
        </span>
      </div>

      <dl className="record-details assignment-insight-details">
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
        {!isCompleted && (
          <>
            <div>
              <dt>Deadline</dt>
              <dd>
                <span
                  className={`deadline-status deadline-status-${assignment.deadline_status.toLowerCase().replaceAll(" ", "-")}`}
                >
                  {assignment.deadline_status}
                </span>
              </dd>
            </div>
            <div>
              <dt>Priority</dt>
              <dd>
                <span className={`priority-badge priority-${assignment.priority.toLowerCase()}`}>
                  {assignment.priority}
                </span>
              </dd>
            </div>
          </>
        )}
        <div>
          <dt>Estimate</dt>
          <dd>{assignment.estimated_hours} hours</dd>
        </div>
      </dl>

      <div className="record-actions">
        <button
          className="button button-secondary button-small"
          type="button"
          onClick={() => onSetCompletion(assignment, !isCompleted)}
          disabled={completionPending}
          aria-label={`${isCompleted ? "Reopen" : "Mark complete"}: ${assignment.name}`}
        >
          {completionPending
            ? isCompleted
              ? "Reopening…"
              : "Completing…"
            : isCompleted
              ? "Reopen"
              : "✓ Mark complete"}
        </button>
        <button
          className="button button-secondary button-small"
          type="button"
          onClick={() => onEdit(assignment)}
          disabled={completionPending}
          aria-label={`Edit assignment ${assignment.name}`}
        >
          Edit
        </button>
        <button
          className="button button-danger button-small"
          type="button"
          onClick={() => onDelete(assignment)}
          disabled={deleting || completionPending}
          aria-label={`Delete assignment ${assignment.name}`}
        >
          {deleting ? "Deleting…" : "Delete"}
        </button>
      </div>
    </article>
  );
}

export default function AssignmentsPage() {
  const [assignments, setAssignments] = useState([]);
  const [courses, setCourses] = useState([]);
  const [formData, setFormData] = useState(emptyAssignmentForm);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [completionId, setCompletionId] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    const requestController = new AbortController();

    Promise.all([
      getAssignmentInsights(requestController.signal),
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

  async function refreshData() {
    const [assignmentData, courseData] = await Promise.all([
      getAssignmentInsights(),
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

  async function handleCompletionChange(assignment, completed) {
    setCompletionId(assignment.id);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      await updateAssignment(assignment.id, {
        name: assignment.name,
        course_id: assignment.course_id,
        due: assignment.due,
        difficulty: assignment.difficulty,
        estimated_hours: assignment.estimated_hours,
        completed,
      });
      if (editingId === assignment.id) {
        setFormData((current) => ({ ...current, completed }));
      }
      await refreshData();
      setSuccessMessage(
        completed
          ? `${assignment.name} was marked complete and moved to Past Assignments.`
          : `${assignment.name} was reopened and moved to Current Assignments.`,
      );
    } catch (error) {
      setErrorMessage(
        getErrorMessage(
          error,
          completed
            ? "The assignment could not be marked complete right now."
            : "The assignment could not be reopened right now.",
        ),
      );
    } finally {
      setCompletionId(null);
    }
  }

  const currentAssignments = assignments.filter(
    (assignment) => !assignment.completed,
  );
  const pastAssignments = getPastAssignments(assignments);

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
        <section
          className="resource-form-panel"
          aria-labelledby="assignment-form-title"
          aria-busy={submitting}
        >
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

        <section
          className="resource-list-panel"
          aria-labelledby="assignment-list-title"
          aria-busy={loading || completionId !== null}
        >
          <div className="list-heading">
            <div>
              <p className="page-eyebrow">Coursework</p>
              <h2 id="assignment-list-title">Assignment history</h2>
            </div>
            <span>{assignments.length} total</span>
          </div>

          {loading ? (
            <LoadingState label="assignments" />
          ) : (
            <>
              <section className="assignment-section" aria-labelledby="current-assignments-title">
                <div className="assignment-section-heading">
                  <div>
                    <p className="page-eyebrow">Active work</p>
                    <h3 id="current-assignments-title">Current Assignments</h3>
                  </div>
                  <span>{currentAssignments.length} open</span>
                </div>

                {currentAssignments.length === 0 ? (
                  <EmptyState
                    mark="A"
                    title="No current assignments"
                    message="Completed work will appear in Past Assignments."
                  />
                ) : (
                  <div className="resource-card-list">
                    {currentAssignments.map((assignment) => (
                      <AssignmentCard
                        assignment={assignment}
                        completionPending={completionId !== null}
                        deleting={deletingId === assignment.id}
                        key={assignment.id}
                        onDelete={handleDelete}
                        onEdit={startEditing}
                        onSetCompletion={handleCompletionChange}
                      />
                    ))}
                  </div>
                )}
              </section>

              <section className="assignment-section" aria-labelledby="past-assignments-title">
                <div className="assignment-section-heading">
                  <div>
                    <p className="page-eyebrow">History</p>
                    <h3 id="past-assignments-title">Past Assignments</h3>
                  </div>
                  <span>{pastAssignments.length} completed</span>
                </div>
                <p className="assignment-history-note">
                  Completed assignments stay in history for seven days and are excluded from workload and study-plan calculations.
                </p>

                {pastAssignments.length === 0 ? (
                  <EmptyState
                    mark="✓"
                    title="No completed assignments"
                    message="Mark an assignment complete to keep it here as history."
                  />
                ) : (
                  <div className="resource-card-list">
                    {pastAssignments.map((assignment) => (
                      <AssignmentCard
                        assignment={assignment}
                        completionPending={completionId !== null}
                        deleting={deletingId === assignment.id}
                        key={assignment.id}
                        onDelete={handleDelete}
                        onEdit={startEditing}
                        onSetCompletion={handleCompletionChange}
                      />
                    ))}
                  </div>
                )}
              </section>
            </>
          )}
        </section>
      </div>
    </section>
  );
}
