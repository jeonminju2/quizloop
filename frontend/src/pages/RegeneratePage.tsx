import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { getQuizSet, getQuizAnalysis, ApiError } from "../api/client";
import type { QuizSet, QuizAnalysis } from "../api/types";
import { CheckIcon, XIcon } from "../components/Icons";
import "./RegeneratePage.css";

interface ConceptDelta {
  concept_id: string;
  concept_name: string;
  before: number; // 0~100
  after: number; // 0~100
}

export default function RegeneratePage() {
  const { quizSetId } = useParams<{ quizSetId: string }>();
  const navigate = useNavigate();

  const [quizSet, setQuizSet] = useState<QuizSet | null>(null);
  const [after, setAfter] = useState<QuizAnalysis | null>(null);
  const [before, setBefore] = useState<QuizAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!quizSetId) return;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const qs = await getQuizSet(quizSetId);
        setQuizSet(qs);
        const afterAnalysis = await getQuizAnalysis(quizSetId);
        setAfter(afterAnalysis);
        if (qs.source_quiz_set_id) {
          const beforeAnalysis = await getQuizAnalysis(qs.source_quiz_set_id);
          setBefore(beforeAnalysis);
        }
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "재출제 결과를 불러오지 못했어요.");
      } finally {
        setLoading(false);
      }
    })();
  }, [quizSetId]);

  if (!quizSetId) return null;

  if (loading) {
    return (
      <div className="content">
        <div className="empty-state">불러오는 중...</div>
      </div>
    );
  }

  if (error || !quizSet || !after) {
    return (
      <div className="content">
        <div className="error-banner">{error ?? "재출제 결과를 표시할 수 없어요."}</div>
      </div>
    );
  }

  const beforeMap = new Map((before?.concept_accuracy ?? []).map((c) => [c.concept_id, c]));
  const deltas: ConceptDelta[] = after.concept_accuracy
    .filter((c) => beforeMap.has(c.concept_id))
    .map((c) => {
      const b = beforeMap.get(c.concept_id)!;
      return {
        concept_id: c.concept_id,
        concept_name: c.concept_name,
        before: Math.round(b.accuracy * 100),
        after: Math.round(c.accuracy * 100),
      };
    });

  const avgBefore = deltas.length ? deltas.reduce((s, d) => s + d.before, 0) / deltas.length : 0;
  const avgAfter = deltas.length ? deltas.reduce((s, d) => s + d.after, 0) / deltas.length : after.accuracy * 100;
  const heroDelta = Math.round(avgAfter - avgBefore);
  const isPositive = heroDelta >= 0;

  const wrongIds = new Set(after.details.map((d) => d.question_id));
  const materialTitle = localStorage.getItem("quizloop:currentMaterialTitle") ?? "";

  const bestImprovement = [...deltas].sort((a, b) => b.after - b.before - (a.after - a.before))[0];

  return (
    <div className="content">
      <div className="page-header">
        <div>
          <div className="eyebrow">{materialTitle || "재출제"} · 재출제 결과</div>
          <h1>재출제 결과</h1>
          <p className="subtitle">취약 개념만 골라 다시 물어봤어요.</p>
        </div>
      </div>

      <div className="card hero-panel">
        <div>
          <div className={"hero-figure" + (isPositive ? " positive" : " negative")}>
            {isPositive ? "+" : ""}
            {heroDelta}%p
          </div>
          <div className="hero-sub">
            {before ? (
              <>
                취약 개념 평균 정답률 <span className="mono">{Math.round(avgBefore)}%</span> →{" "}
                <span className="mono">{Math.round(avgAfter)}%</span>
              </>
            ) : (
              <>이번 세트 정답률 <span className="mono">{Math.round(after.accuracy * 100)}%</span></>
            )}
          </div>
        </div>
        {bestImprovement && (
          <>
            <div className="hero-divider" />
            <p className="hero-note">
              <b>{bestImprovement.concept_name}</b>에서 가장 크게 향상됐어요 ({bestImprovement.before}% →{" "}
              {bestImprovement.after}%).
            </p>
          </>
        )}
      </div>

      {deltas.length > 0 && (
        <div className="card panel">
          <div className="section-title">개념별 정답률 변화</div>
          <p className="section-sub">이전 시도와 재출제 후를 나란히 비교했어요</p>

          <div className="dumbbell-legend">
            <div className="legend-item">
              <span className="legend-dot before" />
              이전 정답률
            </div>
            <div className="legend-item">
              <span className="legend-dot after" />
              재출제 후
            </div>
          </div>

          {deltas.map((d) => {
            const negative = d.after < d.before;
            const lo = Math.min(d.before, d.after);
            const hi = Math.max(d.before, d.after);
            return (
              <div className="dumbbell-row" key={d.concept_id}>
                <div className="dumbbell-label">{d.concept_name}</div>
                <div className="dumbbell-track">
                  <div
                    className={"dumbbell-line" + (negative ? " negative" : "")}
                    style={{ left: `${lo}%`, width: `${hi - lo}%` }}
                  />
                  <div className="dumbbell-dot before" style={{ left: `${d.before}%` }} />
                  <div
                    className={"dumbbell-dot after" + (negative ? " negative" : "")}
                    style={{ left: `${d.after}%` }}
                  />
                  <div className="dumbbell-val before" style={{ left: `${d.before}%` }}>
                    {d.before}%
                  </div>
                  <div className={"dumbbell-val after" + (negative ? " negative" : "")} style={{ left: `${d.after}%` }}>
                    {d.after}%
                  </div>
                </div>
              </div>
            );
          })}

          <div className="dumbbell-axis">
            <span>0%</span>
            <span>25%</span>
            <span>50%</span>
            <span>75%</span>
            <span>100%</span>
          </div>
        </div>
      )}

      <div className="section-title">재출제된 문제</div>
      <p className="section-sub">{quizSet.questions.length}문항</p>

      <div className="card q-card" style={{ marginBottom: 24 }}>
        {quizSet.questions.map((q) => {
          const detail = after.details.find((d) => d.question_id === q.id);
          const isCorrect = !wrongIds.has(q.id);
          return (
            <div className="q-row" key={q.id}>
              <div className={"result-icon " + (isCorrect ? "correct" : "wrong")}>
                {isCorrect ? <CheckIcon size={13} /> : <XIcon size={13} />}
              </div>
              <div className="q-body">
                <p className="q-text">{q.question_text}</p>
                <div className="q-meta">{detail?.source_label && <span className="q-source">근거 · {detail.source_label}</span>}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="footer-actions">
        <Link className="btn btn-ghost" to="/">
          학습 마치기
        </Link>
        {deltas.some((d) => d.after < 80) && (
          <button className="btn btn-primary" onClick={() => navigate(`/analysis/${quizSetId}`)}>
            계속 연습하기
          </button>
        )}
      </div>
    </div>
  );
}
