import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import { RefreshIcon } from "../components/Icons";
import "./AuthPage.css";

const MIN_PASSWORD_LENGTH = 8;

export default function SignupPage() {
  const navigate = useNavigate();
  const { signup } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`비밀번호는 최소 ${MIN_PASSWORD_LENGTH}자 이상이어야 해요.`);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await signup({ email: email.trim(), password, name: name.trim() || undefined });
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "회원가입에 실패했어요.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <form className="auth-card card" onSubmit={handleSubmit}>
        <div className="auth-brand">
          <div className="auth-brand-mark">
            <RefreshIcon size={16} color="#ffffff" />
          </div>
          <div className="auth-brand-word">QuizLoop</div>
        </div>
        <div>
          <h1>회원가입</h1>
          <p className="subtitle">이메일로 계정을 만들고 바로 시작해보세요.</p>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="auth-field">
          <label htmlFor="signup-name">이름 (선택)</label>
          <input id="signup-name" type="text" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="auth-field">
          <label htmlFor="signup-email">이메일</label>
          <input
            id="signup-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="auth-field">
          <label htmlFor="signup-password">비밀번호</label>
          <input
            id="signup-password"
            type="password"
            autoComplete="new-password"
            required
            minLength={MIN_PASSWORD_LENGTH}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <span className="hint">최소 {MIN_PASSWORD_LENGTH}자 이상</span>
        </div>

        <button className="btn btn-primary auth-submit" type="submit" disabled={submitting}>
          {submitting ? "가입 중..." : "회원가입"}
        </button>

        <div className="auth-switch">
          이미 계정이 있으신가요? <Link to="/login">로그인</Link>
        </div>
      </form>
    </div>
  );
}
