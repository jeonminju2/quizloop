import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { getQuizAnalysis, regenerateQuiz, ApiError } from "../api/client";
import type { QuizAnalysis, WrongAnswerTagType } from "../api/types";
import StatTile from "../components/StatTile";
import { WRONG_TYPE_CONFIG } from "../components/WrongTypeBadge";
import { RefreshIcon, SourceIcon } from "../components/Icons";
import "./AnalysisPage.css";

const ICON_CLASS: Record<WrongAnswerTagType, string> = {
  careless_mistake: "warning",
  concept_confusion: "serious",
  not_learned: "critical",
};

export default function AnalysisPage() {
  const params = useParams<{ quizSetId?: string }>();
  const quizSetId = params.quizSetId ?? localStorage.getItem("quizloop:currentQuizSetId") ?? undefined;
  const navigate = useNavigate();

  const [analysis, setAnalysis] = useState<QuizAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    if (!quizSetId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    getQuizAnalysis(quizSetId)
      .then(setAnalysis)
      .catch((e) => setError(e instanceof ApiError ? e.message : "분석 결과를 불러오지 못했어요."))
      .finally(() => setLoading(false));
  }, [quizSetId]);

  async function handleRegenerate() {
    if (!quizSetId) return;
    setRegenerating(true);
    setError(null);
    try {
      const newSet = await regenerateQuiz({ source_quiz_set_id: quizSetId, num_questions: 5 });
      navigate(`/quiz/${newSet.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "재출제에 실패했어요.");
    } finally {
      setRegenerating(false);
    }
  }

  if (!quizSetId) {
    return (
      <div className="content">
        <div className="empty-state">
          아직 채점된 문제가 없어요.
          <br />
          <Link to="/">자료 목록</Link>에서 문제를 풀고 나면 여기서 분석 결과를 볼 수 있어요.
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="content">
        <div className="empty-state">불러오는 중...</div>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="content">
        <div className="error-banner">{error ?? "분석 결과를 표시할 수 없어요."}</div>
      </div>
    );
  }

  const weakConcepts = analysis.concept_accuracy.slice(0, 5);

  return (
    <div className="content">
      <div className="page-header">
        <div>
          <div className="eyebrow">채점 완료</div>
          <h1>오답 분석</h1>
          <p className="subtitle">어디서, 왜 틀렸는지 개념 단위로 짚어드려요.</p>
        </div>
        <button className="btn btn-primary" onClick={handleRegenerate} disabled={regenerating}>
          <RefreshIcon size={14} color="#fff" />
          {regenerating ? "생성 중..." : "취약개념으로 재출제"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="stat-grid">
        <StatTile label="총 문항" value={analysis.total} unit="문항" />
        <StatTile label="정답" value={analysis.correct} unit="문항" />
        <StatTile label="정답률" value={Math.round(analysis.accuracy * 100)} unit="%" accent />
        <StatTile
          label="취약 개념"
          value={analysis.concept_accuracy.filter((c) => c.accuracy < 0.6).length}
          unit="개"
        />
      </div>

      <div className="analysis-grid">
        <div className="card panel">
          <div className="section-title">취약 개념 순위</div>
          <p className="section-sub">개념별 오답률 · 높을수록 재출제 우선순위가 높아요</p>

          {weakConcepts.length === 0 ? (
            <div className="empty-state">집계할 개념이 없어요.</div>
          ) : (
            weakConcepts.map((c) => {
              const wrongPct = Math.round((1 - c.accuracy) * 100);
              return (
                <div className="chart-row" key={c.concept_id}>
                  <div className="chart-label">{c.concept_name}</div>
                  <div className="chart-track">
                    <div className="chart-fill" style={{ width: `${wrongPct}%` }} />
                  </div>
                  <div className="chart-value mono">{wrongPct}%</div>
                </div>
              );
            })
          )}
        </div>

        <div className="card panel">
          <div className="section-title">오답 유형 분포</div>
          <p className="section-sub">틀린 문제 {analysis.details.length}개를 원인별로 나눠봤어요</p>

          {analysis.type_breakdown.length === 0 ? (
            <div className="empty-state">오답이 없어요. 완벽해요!</div>
          ) : (
            analysis.type_breakdown.map((t) => {
              const cfg = WRONG_TYPE_CONFIG[t.tag_type];
              const Icon = cfg.icon;
              return (
                <div className="type-row" key={t.tag_type}>
                  <div className={`type-icon ${ICON_CLASS[t.tag_type]}`}>
                    <Icon size={15} />
                  </div>
                  <div className="type-info">
                    <div className="type-top">
                      <span className="type-label">{cfg.label}</span>
                      <span className="type-count">
                        <b>{t.count}</b>건 · {Math.round(t.pct * 100)}%
                      </span>
                    </div>
                    <div className="type-track">
                      <div
                        className={`type-fill ${ICON_CLASS[t.tag_type]}`}
                        style={{ width: `${t.pct * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      <div className="section-title">문제별 상세</div>
      <p className="section-sub">틀린 문제만 모았어요 · 근거 자료 출처와 함께</p>

      {analysis.details.length === 0 ? (
        <div className="empty-state">틀린 문제가 없어요.</div>
      ) : (
        <div className="card detail-card">
          {analysis.details.map((d) => (
            <div className="detail-row" key={d.question_id}>
              <div className="detail-q">
                <p className="detail-q-text">{d.question_text}</p>
                <div className="detail-answers">
                  <span>
                    <span className="lbl">내 답안</span>
                    <span className="wrong-v">{d.user_answer || "(무응답)"}</span>
                  </span>
                  <span>
                    <span className="lbl">정답</span>
                    <span className="correct-v">{d.correct_answer}</span>
                  </span>
                </div>
                <div className="detail-tags">
                  {d.tag_type && (
                    <span className={`badge ${WRONG_TYPE_CONFIG[d.tag_type].cls}`}>
                      {WRONG_TYPE_CONFIG[d.tag_type].label}
                    </span>
                  )}
                  {d.source_label && (
                    <span className="source-chip">
                      <SourceIcon />
                      근거 · {d.source_label}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
