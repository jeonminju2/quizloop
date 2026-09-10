// FastAPI 백엔드(backend/app) 호출 래퍼.
// 아직 인증이 없어서(백엔드 라우터가 user_id를 쿼리 파라미터로 받음) 데모용 고정 user_id를 씀.
// TODO: 로그인 붙이면 이 부분을 실제 로그인 유저 id로 교체.

import type {
  Material,
  QuizGenerateRequest,
  QuizSet,
  SubmissionCreate,
  Submission,
  RegenerateRequest,
  QuizAnalysis,
} from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// 데모용 고정 user_id. 백엔드 users 테이블에 이 id로 미리 시드해두고 쓰는 걸 가정.
export const DEMO_USER_ID = import.meta.env.VITE_DEMO_USER_ID ?? "00000000-0000-0000-0000-000000000001";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
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

function withUser(path: string, params: Record<string, string | number | undefined> = {}) {
  const qs = new URLSearchParams({ user_id: DEMO_USER_ID });
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) qs.set(k, String(v));
  }
  return `${path}?${qs.toString()}`;
}

// ---------- Materials ----------

export function listMaterials(): Promise<Material[]> {
  return request(withUser("/materials"));
}

export function uploadMaterial(file: File): Promise<Material> {
  const form = new FormData();
  form.append("file", file);
  return request(withUser("/materials/upload"), { method: "POST", body: form });
}

// ---------- Quiz ----------

export function getQuizSet(quizSetId: string): Promise<QuizSet> {
  return request(`/quiz-sets/${quizSetId}`);
}

export function generateQuiz(req: QuizGenerateRequest): Promise<QuizSet> {
  return request(withUser("/quiz-sets/generate"), {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function submitQuiz(quizSetId: string, body: SubmissionCreate): Promise<Submission> {
  return request(withUser(`/quiz-sets/${quizSetId}/submit`), {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function regenerateQuiz(req: RegenerateRequest): Promise<QuizSet> {
  return request(withUser("/quiz-sets/regenerate"), {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function getQuizAnalysis(quizSetId: string): Promise<QuizAnalysis> {
  return request(withUser(`/quiz-sets/${quizSetId}/analysis`));
}
