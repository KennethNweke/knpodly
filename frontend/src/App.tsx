import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import LoginPage from "./pages/LoginPage";
import StudentDashboardPage from "./pages/StudentDashboardPage";
import LecturerDashboardPage from "./pages/LecturerDashboardPage";
import AdminPage from "./pages/AdminPage";
import ConsolePage from "./pages/ConsolePage";
import AppLayout from "./components/common/AppLayout";

function ProtectedRoute({ children, roles }: { children: JSX.Element; roles?: string[] }) {
  const { user, loading } = useAuth();
  if (loading) return null; // avoid a login-page flash while /auth/me resolves
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "student") return <Navigate to="/dashboard" replace />;
  return <Navigate to="/lecturer" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<AppLayout />}>
          <Route path="/" element={<HomeRedirect />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute roles={["student", "lecturer", "admin"]}>
                <StudentDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/lecturer"
            element={
              <ProtectedRoute roles={["lecturer", "admin"]}>
                <LecturerDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute roles={["admin"]}>
                <AdminPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/console/:sessionId"
            element={
              <ProtectedRoute roles={["student", "lecturer", "admin"]}>
                <ConsolePage />
              </ProtectedRoute>
            }
          />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
