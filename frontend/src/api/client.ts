// FastAPI 백엔드(backend/app) 호출 래퍼.
// 백엔드가 JWT 인증을 요구하므로(app/deps.py의 get_current_user) 로그인 시 발급받은
// access_token을 localStorage에 저장해두고 모든 요청에 Authorization: Bearer로 붙인다.

import type {
  Material,
  MaterialUpdate,
  QuizGenerateRequest,
  QuizSet,
  SubmissionCreate,
  Submission,
  RegenerateRequest,
  QuizAnalysis,
  SignupRequest,
  LoginRequest,
  TokenOut,
  User,
} from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const TOKEN_STORAGE_KEY = "quizloop:token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    // 프라이빗 모드 등에서 localStorage 접근이 막혀있을 수 있음 — 로그인 안 된 것처럼 취급
    return null;
  }
}

function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
    else localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // 저장 실패해도 메모리상 로그인 상태(React state)는 이번 세션 동안 유지됨
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // 응답이 JSON이 아니면 statusText 그대로 사용
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---------- Auth ----------

export async function signup(body: SignupRequest): Promise<User> {
  const token = await request<TokenOut>("/auth/signup", { method: "POST", body: JSON.stringify(body) });
  setToken(token.access_token);
  return getMe();
}

export async function login(body: LoginRequest): Promise<User> {
  const token = await request<TokenOut>("/auth/login", { method: "POST", body: JSON.stringify(body) });
  setToken(token.access_token);
  return getMe();
}

export function getMe(): Promise<User> {
  return request("/auth/me");
}

export function logout() {
  setToken(null);
}

// ---------- Materials ----------

export function listMaterials(): Promise<Material[]> {
  return request("/materials");
}

export function uploadMaterial(file: File, examStyleNote?: string): Promise<Material> {
  const form = new FormData();
  form.append("file", file);
  if (examStyleNote && examStyleNote.trim()) form.append("exam_style_note", examStyleNote.trim());
  return request("/materials/upload", { method: "POST", body: form });
}

export function updateMaterial(materialId: string, body: MaterialUpdate): Promise<Material> {
  return request(`/materials/${materialId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ---------- Quiz ----------

export function getQuizSet(quizSetId: string): Promise<QuizSet> {
  return request(`/quiz-sets/${quizSetId}`);
}

export function generateQuiz(req: QuizGenerateRequest): Promise<QuizSet> {
  return request("/quiz-sets/generate", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function submitQuiz(quizSetId: string, body: SubmissionCreate): Promise<Submission> {
  return request(`/quiz-sets/${quizSetId}/submit`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function regenerateQuiz(req: RegenerateRequest): Promise<QuizSet> {
  return request("/quiz-sets/regenerate", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function getQuizAnalysis(quizSetId: string): Promise<QuizAnalysis> {
  return request(`/quiz-sets/${quizSetId}/analysis`);
}
