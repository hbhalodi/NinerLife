import { useEffect, useState } from "react";

import Notice from "../components/Notice";
import { EmptyState, LoadingState } from "../components/ResourceStates";
import { getErrorMessage } from "../services/api";
import { getStudyPlan } from "../services/studyPlan";

function formatDate(value) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(`${value}T00:00:00`));
}

function formatHours(value) {
  return Number.isInteger(value) ? value : value.toFixed(2);
}

export default function StudyPlanPage() {
  const [plan, setPlan] = useState(null);
  const [availableHours, setAvailableHours] = useState("4");
  const [horizonDays, setHorizonDays] = useState("7");
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  async function loadPlan(options = {}) {
    setLoading(true);
    setErrorMessage("");

    try {
      const data = await getStudyPlan(options);
      setPlan(data);
    } catch (error) {
      if (error.name !== "AbortError") {
        setErrorMessage(
          getErrorMessage(error, "Your study plan could not be loaded right now."),
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
    loadPlan({ signal: requestController.signal });
    return () => requestController.abort();
  }, []);

  function handleSubmit(event) {
    event.preventDefault();
    const parsedAvailableHours = Number(availableHours);
    const parsedHorizonDays = Number(horizonDays);

    if (
      availableHours === "" ||
      !Number.isFinite(parsedAvailableHours) ||
      parsedAvailableHours <= 0
    ) {
      setErrorMessage("Available study hours must be greater than zero.");
      return;
    }
    if (
      horizonDays === "" ||
      !Number.isInteger(parsedHorizonDays) ||
      parsedHorizonDays < 1 ||
      parsedHorizonDays > 30
    ) {
      setErrorMessage("Horizon days must be a whole number from 1 to 30.");
      return;
    }

    loadPlan({
      availableHours: parsedAvailableHours,
      horizonDays: parsedHorizonDays,
    });
  }

  return (
    <section className="page-stack" aria-labelledby="study-plan-title">
      <div className="resource-page-heading">
        <div>
          <p className="page-eyebrow">Focused planning</p>
          <h1 id="study-plan-title">What should I work on next?</h1>
          <p>
            A transparent order based on dates, difficulty, item type, and the
            time you have available.
          </p>
        </div>
        {plan && (
          <div className="resource-count" aria-label="Plan recommendations">
            <strong>{plan.recommendations.length}</strong>
            <span>items</span>
          </div>
        )}
      </div>

      <Notice type="error" message={errorMessage} />

      <section className="study-plan-controls" aria-labelledby="study-plan-controls-title">
        <div>
          <p className="page-eyebrow">Plan settings</p>
          <h2 id="study-plan-controls-title">Make time for what matters</h2>
        </div>
        <form className="study-plan-form" onSubmit={handleSubmit}>
          <label className="form-field">
            <span>Available study hours</span>
            <input
              type="number"
              min="0.25"
              step="0.25"
              value={availableHours}
              onChange={(event) => setAvailableHours(event.target.value)}
              required
            />
          </label>
          <label className="form-field">
            <span>Plan horizon (days)</span>
            <input
              type="number"
              min="1"
              max="30"
              step="1"
              value={horizonDays}
              onChange={(event) => setHorizonDays(event.target.value)}
              required
            />
          </label>
          <button className="button button-primary" disabled={loading} type="submit">
            {loading ? "Refreshing…" : "Generate plan"}
          </button>
        </form>
      </section>

      {loading && plan === null ? (
        <section className="study-plan-panel">
          <LoadingState label="study plan" />
        </section>
      ) : plan === null ? (
        <section className="study-plan-panel">
          <EmptyState
            mark="!"
            title="Study plan unavailable"
            message="Check the backend connection and try again."
          />
        </section>
      ) : (
        <>
          <section className="study-plan-summary" aria-label="Study plan summary">
            <div>
              <span>Available</span>
              <strong>{formatHours(plan.available_hours)} hours</strong>
            </div>
            <div>
              <span>Allocated</span>
              <strong>{formatHours(plan.allocated_hours)} hours</strong>
            </div>
            <div>
              <span>Remaining</span>
              <strong>{formatHours(plan.remaining_hours)} hours</strong>
            </div>
            <div>
              <span>Horizon</span>
              <strong>{plan.horizon_days} days</strong>
            </div>
          </section>

          <section className="study-plan-panel" aria-labelledby="recommendations-title">
            <div className="list-heading">
              <div>
                <p className="page-eyebrow">Ordered recommendations</p>
                <h2 id="recommendations-title">Your next study steps</h2>
              </div>
              <span>{plan.recommendations.length} total</span>
            </div>

            {plan.recommendations.length === 0 ? (
              <EmptyState
                mark="✓"
                title="No study items need attention"
                message="There are no incomplete assignments or exams in this plan window."
              />
            ) : (
              <ol className="study-plan-list">
                {plan.recommendations.map((recommendation, index) => (
                  <li className="study-plan-item" key={`${recommendation.type}-${recommendation.id}`}>
                    <div className="study-plan-order" aria-label={`Recommendation ${index + 1}`}>
                      {index + 1}
                    </div>
                    <article>
                      <div className="record-card-heading">
                        <div>
                          <p className="record-context">
                            {recommendation.course.code} — {recommendation.course.name}
                          </p>
                          <h3>{recommendation.name}</h3>
                        </div>
                        <span
                          className={`plan-item-type plan-item-type-${recommendation.type.toLowerCase()}`}
                        >
                          {recommendation.type}
                        </span>
                      </div>

                      <dl className="study-plan-details">
                        <div>
                          <dt>Date</dt>
                          <dd>{formatDate(recommendation.date)}</dd>
                        </div>
                        <div>
                          <dt>Difficulty</dt>
                          <dd>
                            <span className={`difficulty difficulty-${recommendation.difficulty.toLowerCase()}`}>
                              {recommendation.difficulty}
                            </span>
                          </dd>
                        </div>
                        <div>
                          <dt>Score</dt>
                          <dd>{recommendation.score}</dd>
                        </div>
                        <div>
                          <dt>Estimated</dt>
                          <dd>{formatHours(recommendation.estimated_hours)} hours</dd>
                        </div>
                        <div>
                          <dt>Study next</dt>
                          <dd>{formatHours(recommendation.recommended_study_hours)} hours</dd>
                        </div>
                      </dl>

                      <div className="study-plan-reasons">
                        <h4>Why this is here</h4>
                        <ul>
                          {recommendation.reasons.map((reason) => (
                            <li key={reason}>{reason}</li>
                          ))}
                        </ul>
                      </div>
                    </article>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </>
      )}
    </section>
  );
}
