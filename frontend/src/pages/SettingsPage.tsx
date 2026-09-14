import { useAuth } from "../auth/AuthContext";

export default function SettingsPage() {
  const { user, logout } = useAuth();

  return (
    <div className="content">
      <div className="page-header">
        <div>
          <div className="eyebrow">설정</div>
          <h1>설정</h1>
          <p className="subtitle">계정 정보를 확인하고 로그아웃할 수 있어요.</p>
        </div>
      </div>

      <div className="card" style={{ padding: 24, maxWidth: 420 }}>
        <div className="section-title">계정</div>
        <p className="section-sub" style={{ marginBottom: 16 }}>
          {user?.name ? `${user.name} · ` : ""}
          {user?.email}
        </p>
        <button className="btn btn-ghost" onClick={logout}>
          로그아웃
        </button>
      </div>
    </div>
  );
}
