import { useEffect, useState } from "react";

import Notice from "../components/Notice";
import { EmptyState, LoadingState } from "../components/ResourceStates";
import { getErrorMessage } from "../services/api";
import { getDashboardSummary } from "../services/dashboard";

function formatDate(value) {
  if (!value) {
    return "Date unavailable";
  }

  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

function getBadgeClass(value, prefix) {
  if (typeof value !== "string" || value.trim() === "") {
    return null;
  }

  return `${prefix}-${value.toLowerCase().replaceAll(" ", "-")}`;
}

function MetricCard({ label, value, detail }) {
  return (
    <article className="dashboard-metric-card">
      <p>{label}</p>
      <strong>{value}</strong>
      <span>{detail}</span>
    </article>
  );
}

function UpcomingList({ type, records }) {
  const isAssignment = type === "assignment";
  const title = isAssignment ? "Upcoming Assignments" : "Upcoming Exams";

  return (
    <section className="dashboard-upcoming-panel" aria-labelledby={`${type}-heading`}>
      <div className="list-heading">
        <div>
          <p className="page-eyebrow">Next seven days</p>
          <h2 id={`${type}-heading`}>{title}</h2>
        </div>
        <span>{records.length} upcoming</span>
      </div>

      {records.length === 0 ? (
        <EmptyState
          mark={isAssignment ? "A" : "E"}
          title={`No upcoming ${isAssignment ? "assignments" : "exams"}`}
          message="Nothing incomplete is scheduled in the next seven days."
        />
      ) : (
        <div className="dashboard-upcoming-list">
          {records.map((record) => {
            const dateValue = isAssignment ? record.due : record.exam_date;
            const courseLabel = [record.course?.code, record.course?.name]
              .filter(Boolean)
              .join(" — ") || "Course unavailable";
            const deadlineClass = getBadgeClass(
              record.deadline_status,
              "deadline-status",
            );
            const priorityClass = getBadgeClass(record.priority, "priority");
            const difficultyClass = getBadgeClass(record.difficulty, "difficulty");

            return (
              <article className="dashboard-upcoming-item" key={record.id}>
                <div>
                  <p className="record-context">{courseLabel}</p>
                  <h3>{record.name}</h3>
                </div>
                <div className="dashboard-upcoming-meta">
                  <time dateTime={dateValue}>{formatDate(dateValue)}</time>
                  <div className="dashboard-upcoming-labels">
                    {isAssignment && deadlineClass && (
                      <span
                        className={`deadline-status ${deadlineClass}`}
                        aria-label={`Deadline status: ${record.deadline_status}`}
                      >
                        {record.deadline_status}
                      </span>
                    )}
                    {isAssignment && priorityClass && (
                      <span
                        className={`priority-badge ${priorityClass}`}
                        aria-label={`Priority: ${record.priority}`}
                      >
                        {record.priority}
                      </span>
                    )}
                    {difficultyClass && (
                      <span
                        className={`difficulty ${difficultyClass}`}
                        aria-label={`Difficulty: ${record.difficulty}`}
                      >
                        {record.difficulty}
                      </span>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [workHours, setWorkHours] = useState("0");
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  async function loadSummary(options = {}) {
    setLoading(true);
    setErrorMessage("");

    try {
      const data = await getDashboardSummary(options);
      setSummary(data);
    } catch (error) {
      if (error.name !== "AbortError") {
        setErrorMessage(
          getErrorMessage(error, "Dashboard data could not be loaded right now."),
        );
      }
    } finally {
      if (!options.signal?.aborted) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    const requestController = new AbortController();
    loadSummary({ signal: requestController.signal });
    return () => requestController.abort();
  }, []);

  function handleWorkHoursSubmit(event) {
    event.preventDefault();
    const parsedWorkHours = Number(workHours);

    if (workHours === "" || !Number.isFinite(parsedWorkHours) || parsedWorkHours < 0) {
      setErrorMessage("Work hours must be zero or greater.");
      return;
    }

    loadSummary({ workHours: parsedWorkHours });
  }

  return (
    <section className="page-stack" aria-labelledby="dashboard-title">
      <div className="dashboard-heading">
        <div>
          <p className="page-eyebrow">Dashboard</p>
          <h1 id="dashboard-title">Know what comes next.</h1>
          <p>
            Your focused view of coursework, deadlines, and academic momentum.
          </p>
        </div>
        <span className="foundation-badge">Live summary</span>
      </div>

      <Notice type="error" message={errorMessage} />

      {loading && summary === null ? (
        <section className="dashboard-state-panel">
          <LoadingState label="dashboard" />
        </section>
      ) : summary === null ? (
        <section className="dashboard-state-panel">
          <EmptyState
            mark="!"
            title="Dashboard unavailable"
            message="Check the backend connection and try again."
          />
        </section>
      ) : (
        <>
          <div className="dashboard-metrics">
            <MetricCard
              label="Active Courses"
              value={summary.total_course_count}
              detail="All current courses"
            />
            <MetricCard
              label="Assignments This Week"
              value={summary.weekly_assignment_count}
              detail="Incomplete and due soon"
            />
            <MetricCard
              label="Exams This Week"
              value={summary.weekly_exam_count}
              detail="Incomplete and scheduled soon"
            />
            <MetricCard
              label="Overdue Assignments"
              value={summary.overdue_incomplete_assignment_count}
              detail="Incomplete and past due"
            />
          </div>

          <section className="workload-panel" aria-labelledby="workload-heading">
            <div className="workload-summary">
              <p className="page-eyebrow">Weekly workload</p>
              <div className="workload-score-row">
                <strong>{summary.workload_score}</strong>
                <span
                  className={`workload-level workload-level-${summary.workload_level.toLowerCase()}`}
                >
                  {summary.workload_level}
                </span>
              </div>
              <h2 id="workload-heading">Your workload score</h2>
              <p>
                Based on active courses, incomplete work through {formatDate(summary.window_end)},
                and {summary.work_hours} work hours.
              </p>
            </div>

            <form
              className="work-hours-form"
              onSubmit={handleWorkHoursSubmit}
              aria-busy={loading}
            >
              <label className="form-field">
                <span>Work hours this week</span>
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  value={workHours}
                  onChange={(event) => setWorkHours(event.target.value)}
                  required
                />
              </label>
              <button className="button button-primary" disabled={loading} type="submit">
                {loading ? "Updating…" : "Update summary"}
              </button>
            </form>
          </section>

          <div className="dashboard-upcoming-grid">
            <UpcomingList
              type="assignment"
              records={summary.upcoming_assignments}
            />
            <UpcomingList type="exam" records={summary.upcoming_exams} />
          </div>
        </>
      )}

      <aside className="next-step-panel">
        <p className="page-eyebrow">Today’s focus</p>
        <h2>Know what matters. Know what comes next.</h2>
        <p>
          Use this weekly view to understand what is approaching without changing
          any of your course records.
        </p>
      </aside>
    </section>
  );
}
