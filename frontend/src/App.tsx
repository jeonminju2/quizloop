import type { ReactNode } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import MaterialsPage from "./pages/MaterialsPage";
import QuizPage from "./pages/QuizPage";
import AnalysisPage from "./pages/AnalysisPage";
import RegeneratePage from "./pages/RegeneratePage";
import SettingsPage from "./pages/SettingsPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import { AuthProvider, useAuth } from "./auth/AuthContext";

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <div className="empty-state">불러오는 중...</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function AppShell() {
  return (
    <RequireAuth>
      <div className="app-shell">
        <Sidebar />
        <Routes>
          <Route path="/" element={<MaterialsPage />} />
          <Route path="/quiz" element={<QuizPage />} />
          <Route path="/quiz/:quizSetId" element={<QuizPage />} />
          <Route path="/analysis" element={<AnalysisPage />} />
          <Route path="/analysis/:quizSetId" element={<AnalysisPage />} />
          <Route path="/regenerate/:quizSetId" element={<RegeneratePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </RequireAuth>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/*" element={<AppShell />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
