import { NavLink, Outlet, useLocation } from "react-router-dom";

import BackendStatus from "./BackendStatus";

const navigationItems = [
  { label: "Dashboard", path: "/", shortLabel: "DB" },
  { label: "Assignments", path: "/assignments", shortLabel: "AS" },
  { label: "Courses", path: "/courses", shortLabel: "CO" },
  { label: "Exams", path: "/exams", shortLabel: "EX" },
  { label: "Study Plan", path: "/study-plan", shortLabel: "SP" },
];

const pageTitles = {
  "/": "Your academic overview",
  "/assignments": "Assignments",
  "/courses": "Courses",
  "/exams": "Exams",
  "/study-plan": "Study plan",
};

export default function AppShell() {
  const location = useLocation();
  const pageTitle = pageTitles[location.pathname] ?? "NinerLife";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">
            N
          </span>
          <div>
            <p className="brand-name">NinerLife</p>
            <p className="brand-edition">Student planner</p>
          </div>
        </div>

        <nav className="primary-navigation" aria-label="Primary navigation">
          {navigationItems.map((item) => (
            <NavLink
              className={({ isActive }) =>
                `navigation-link${isActive ? " navigation-link-active" : ""}`
              }
              end={item.path === "/"}
              key={item.path}
              to={item.path}
            >
              <span className="navigation-symbol" aria-hidden="true">
                {item.shortLabel}
              </span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <p className="sidebar-motto">
          Know what matters.
          <br />
          Know what comes next.
        </p>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div>
            <p className="topbar-eyebrow">Welcome to NinerLife</p>
            <p className="topbar-title">{pageTitle}</p>
          </div>
          <BackendStatus />
        </header>

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
