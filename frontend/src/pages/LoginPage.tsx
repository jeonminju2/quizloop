import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import { RefreshIcon } from "../components/Icons";
import "./AuthPage.css";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login({ email: email.trim(), password });
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "로그인에 실패했어요.");
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
          <h1>로그인</h1>
          <p className="subtitle">강의자료로 만든 나만의 문제로 시험을 준비해요.</p>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="auth-field">
          <label htmlFor="login-email">이메일</label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="auth-field">
          <label htmlFor="login-password">비밀번호</label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <button className="btn btn-primary auth-submit" type="submit" disabled={submitting}>
          {submitting ? "로그인 중..." : "로그인"}
        </button>

        <div className="auth-switch">
          아직 계정이 없으신가요? <Link to="/signup">회원가입</Link>
        </div>
      </form>
    </div>
  );
}
