// 로그인 상태를 앱 전체에서 공유하기 위한 컨텍스트.
// 앱이 처음 뜰 때 localStorage에 토큰이 남아있으면(api/client.ts) /auth/me로 검증해서
// 자동 로그인을 시도하고, 없거나 만료됐으면 로그인 화면으로 보낸다 (App.tsx의 RequireAuth 참고).

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import * as api from "../api/client";
import type { LoginRequest, SignupRequest, User } from "../api/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (body: LoginRequest) => Promise<void>;
  signup: (body: SignupRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      if (!api.getToken()) {
        setLoading(false);
        return;
      }
      try {
        const me = await api.getMe();
        if (!cancelled) setUser(me);
      } catch {
        // 토큰이 만료/무효 — 조용히 로그아웃 상태로 되돌림
        api.logout();
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (body: LoginRequest) => {
    const me = await api.login(body);
    setUser(me);
  }, []);

  const signup = useCallback(async (body: SignupRequest) => {
    const me = await api.signup(body);
    setUser(me);
  }, []);

  const logout = useCallback(() => {
    api.logout();
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, login, signup, logout }), [user, loading, login, signup, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth는 AuthProvider 안에서만 사용할 수 있어요.");
  return ctx;
}
