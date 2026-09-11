import { Navigate, Route, Routes } from "react-router-dom";

import AppShell from "./components/AppShell";
import AssignmentsPage from "./pages/AssignmentsPage";
import CoursesPage from "./pages/CoursesPage";
import DashboardPage from "./pages/DashboardPage";
import ExamsPage from "./pages/ExamsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="assignments" element={<AssignmentsPage />} />
        <Route path="courses" element={<CoursesPage />} />
        <Route path="exams" element={<ExamsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
