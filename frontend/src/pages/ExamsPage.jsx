import { useEffect, useState } from "react";

import Notice from "../components/Notice";
import ResourceHeader from "../components/ResourceHeader";
import { EmptyState, LoadingState } from "../components/ResourceStates";
import { getErrorMessage } from "../services/api";
import { getCourses } from "../services/courses";
import { createExam, deleteExam, getExams, updateExam } from "../services/exams";

const emptyExamForm = {
  name: "",
  course_id: "",
  exam_date: "",
  difficulty: "Medium",
  estimated_study_hours: "",
  completed: false,
};

function formatDate(value) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}

export default function ExamsPage() {
  const [exams, setExams] = useState([]);
  const [courses, setCourses] = useState([]);
  const [formData, setFormData] = useState(emptyExamForm);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    const requestController = new AbortController();

    Promise.all([
      getExams(requestController.signal),
      getCourses(requestController.signal),
    ])
      .then(([examData, courseData]) => {
        setExams(examData);
        setCourses(courseData);
      })
      .catch((error) => {
        if (error.name !== "AbortError") {
          setErrorMessage(
            getErrorMessage(error, "Exams could not be loaded right now."),
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
    const [examData, courseData] = await Promise.all([getExams(), getCourses()]);
    setExams(examData);
    setCourses(courseData);
  }

  function resetForm() {
    setFormData(emptyExamForm);
    setEditingId(null);
  }

  function startEditing(exam) {
    setFormData({
      name: exam.name,
      course_id: String(exam.course_id),
      exam_date: exam.exam_date,
      difficulty: exam.difficulty,
      estimated_study_hours: String(exam.estimated_study_hours),
      completed: exam.completed,
    });
    setEditingId(exam.id);
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
    const studyHours = Number(formData.estimated_study_hours);

    setErrorMessage("");
    setSuccessMessage("");

    if (!formData.name.trim()) {
      setErrorMessage("Exam name is required.");
      return;
    }

    if (!formData.course_id || !formData.exam_date) {
      setErrorMessage("Choose a course and exam date.");
      return;
    }

    if (!Number.isFinite(studyHours) || studyHours < 0) {
      setErrorMessage("Estimated study hours must be zero or greater.");
      return;
    }

    const payload = {
      name: formData.name.trim(),
      course_id: Number(formData.course_id),
      exam_date: formData.exam_date,
      difficulty: formData.difficulty,
      estimated_study_hours: studyHours,
      completed: formData.completed,
    };

    setSubmitting(true);

    try {
      if (editingId === null) {
        await createExam(payload);
        setSuccessMessage(`${payload.name} was added.`);
      } else {
        await updateExam(editingId, payload);
        setSuccessMessage(`${payload.name} was updated.`);
      }

      resetForm();
      await refreshData();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "The exam could not be saved right now."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(exam) {
    const confirmed = window.confirm(`Delete ${exam.name}? This cannot be undone.`);

    if (!confirmed) {
      return;
    }

    setDeletingId(exam.id);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      await deleteExam(exam.id);
      if (editingId === exam.id) {
        resetForm();
      }
      await refreshData();
      setSuccessMessage(`${exam.name} was deleted.`);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "The exam could not be deleted right now."));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="page-stack" aria-labelledby="exams-title">
      <ResourceHeader
        eyebrow="Preparation"
        title="Exams"
        description="Track exam dates, study effort, and completion."
        count={exams.length}
        singularLabel="exam"
        titleId="exams-title"
      />

      <Notice type="error" message={errorMessage} />
      <Notice type="success" message={successMessage} />

      <div className="resource-workspace resource-workspace-wide-form">
        <section
          className="resource-form-panel"
          aria-labelledby="exam-form-title"
          aria-busy={submitting}
        >
          <div className="panel-heading">
            <p className="page-eyebrow">{editingId === null ? "Add new" : "Editing"}</p>
            <h2 id="exam-form-title">
              {editingId === null ? "Add an exam" : "Update exam"}
            </h2>
            <p>Record the date and study time you expect to need.</p>
          </div>

          {courses.length === 0 && !loading && (
            <Notice type="error" message="Add a course before creating an exam." />
          )}

          <form className="resource-form" onSubmit={handleSubmit}>
            <label className="form-field form-field-full">
              <span>Exam name</span>
              <input
                name="name"
                value={formData.name}
                onChange={updateFormField}
                placeholder="Midterm exam"
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
              <span>Exam date</span>
              <input
                name="exam_date"
                type="date"
                value={formData.exam_date}
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
              <span>Estimated study hours</span>
              <input
                name="estimated_study_hours"
                type="number"
                min="0"
                step="0.25"
                value={formData.estimated_study_hours}
                onChange={updateFormField}
                placeholder="6"
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
                    ? "Add exam"
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

        <section className="resource-list-panel" aria-labelledby="exam-list-title">
          <div className="list-heading">
            <div>
              <p className="page-eyebrow">Exam schedule</p>
              <h2 id="exam-list-title">All exams</h2>
            </div>
            <span>{exams.length} total</span>
          </div>

          {loading ? (
            <LoadingState label="exams" />
          ) : exams.length === 0 ? (
            <EmptyState
              mark="E"
              title="No exams yet"
              message="Your exam schedule is clear. Add an exam when a date is announced."
            />
          ) : (
            <div className="resource-card-list">
              {exams.map((exam) => (
                <article className="resource-card record-card" key={exam.id}>
                  <div className="record-card-heading">
                    <div>
                      <p className="record-context">
                        {courseNames.get(exam.course_id) ?? `Course #${exam.course_id}`}
                      </p>
                      <h3>{exam.name}</h3>
                    </div>
                    <span className={`completion-badge ${exam.completed ? "is-complete" : ""}`}>
                      {exam.completed ? "Completed" : "Open"}
                    </span>
                  </div>

                  <dl className="record-details">
                    <div>
                      <dt>Date</dt>
                      <dd>{formatDate(exam.exam_date)}</dd>
                    </div>
                    <div>
                      <dt>Difficulty</dt>
                      <dd>
                        <span className={`difficulty difficulty-${exam.difficulty.toLowerCase()}`}>
                          {exam.difficulty}
                        </span>
                      </dd>
                    </div>
                    <div>
                      <dt>Study estimate</dt>
                      <dd>{exam.estimated_study_hours} hours</dd>
                    </div>
                  </dl>

                  <div className="record-actions">
                    <button
                      className="button button-secondary button-small"
                      type="button"
                      onClick={() => startEditing(exam)}
                      aria-label={`Edit exam ${exam.name}`}
                    >
                      Edit
                    </button>
                    <button
                      className="button button-danger button-small"
                      type="button"
                      onClick={() => handleDelete(exam)}
                      disabled={deletingId === exam.id}
                      aria-label={`Delete exam ${exam.name}`}
                    >
                      {deletingId === exam.id ? "Deleting…" : "Delete"}
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
