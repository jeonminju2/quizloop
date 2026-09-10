import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import MaterialsPage from "./pages/MaterialsPage";
import QuizPage from "./pages/QuizPage";
import AnalysisPage from "./pages/AnalysisPage";
import RegeneratePage from "./pages/RegeneratePage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <BrowserRouter>
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
        </Routes>
      </div>
    </BrowserRouter>
  );
}
