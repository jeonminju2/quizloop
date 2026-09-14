import { NavLink } from "react-router-dom";
import { MaterialsIcon, QuizIcon, AnalysisIcon, SettingsIcon, RefreshIcon } from "./Icons";
import { useAuth } from "../auth/AuthContext";
import "./Sidebar.css";

const NAV_ITEMS = [
  { to: "/", label: "자료", icon: MaterialsIcon, end: true },
  { to: "/quiz", label: "문제풀이", icon: QuizIcon },
  { to: "/analysis", label: "오답분석", icon: AnalysisIcon },
  { to: "/settings", label: "설정", icon: SettingsIcon },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const displayName = user?.name?.trim() || user?.email || "";
  const avatarLabel = displayName.slice(0, 2) || "?";

  return (
    <aside className="sidebar">
      <div className="brand-row">
        <div className="brand-mark">
          <RefreshIcon size={16} color="#ffffff" />
        </div>
        <div className="brand-word">QuizLoop</div>
      </div>

      <nav className="nav">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-foot">
        <div className="avatar">{avatarLabel}</div>
        <div>
          <div className="user-name">{displayName || "게스트"}</div>
          <div className="user-role">{user?.email ?? ""}</div>
        </div>
        <button className="btn btn-ghost small sidebar-logout" onClick={logout}>
          로그아웃
        </button>
      </div>
    </aside>
  );
}
