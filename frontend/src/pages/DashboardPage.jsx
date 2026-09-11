const dashboardSections = [
  "Weekly Workload",
  "Upcoming Assignments",
  "High Priority",
  "Upcoming Exams",
];

export default function DashboardPage() {
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
        <span className="foundation-badge">Foundation</span>
      </div>

      <div className="dashboard-grid">
        {dashboardSections.map((section, index) => (
          <article className="dashboard-card" key={section}>
            <div className="card-heading-row">
              <span className="card-number">0{index + 1}</span>
              <span className="card-rule" />
            </div>
            <h2>{section}</h2>
            <p>Dashboard data will appear here.</p>
          </article>
        ))}
      </div>

      <aside className="next-step-panel">
        <p className="page-eyebrow">Today’s focus</p>
        <h2>Your recommendations will live here.</h2>
        <p>
          NinerLife will eventually bring your most important academic work into
          one clear view.
        </p>
      </aside>
    </section>
  );
}
