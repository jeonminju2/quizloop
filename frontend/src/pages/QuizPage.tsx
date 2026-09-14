import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { getQuizSet, submitQuiz, ApiError } from "../api/client";
import type { QuizSet } from "../api/types";
import { ChevronRightIcon, TargetIcon } from "../components/Icons";
import "./QuizPage.css";

export default function QuizPage() {
  const params = useParams<{ quizSetId?: string }>();
  const quizSetId = params.quizSetId ?? localStorage.getItem("quizloop:currentQuizSetId") ?? undefined;
  const navigate = useNavigate();

  const [quizSet, setQuizSet] = useState<QuizSet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!quizSetId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    getQuizSet(quizSetId)
      .then((qs) => {
        setQuizSet(qs);
        localStorage.setItem("quizloop:currentQuizSetId", qs.id);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "문제를 불러오지 못했어요."))
      .finally(() => setLoading(false));
  }, [quizSetId]);

  const question = quizSet?.questions[index];
  const materialTitle = localStorage.getItem("quizloop:currentMaterialTitle") ?? "";

  const answeredCount = useMemo(
    () => quizSet?.questions.filter((q) => answers[q.id]).length ?? 0,
    [quizSet, answers]
  );

  if (!quizSetId) {
    return (
      <div className="content quiz-content">
        <div className="empty-state">
          아직 진행 중인 문제 세트가 없어요.
          <br />
          <Link to="/">자료 목록</Link>에서 먼저 문제를 생성해주세요.
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="content quiz-content">
        <div className="empty-state">불러오는 중...</div>
      </div>
    );
  }

  if (error || !quizSet || !question) {
    return (
      <div className="content quiz-content">
        <div className="error-banner">{error ?? "문제를 표시할 수 없어요."}</div>
      </div>
    );
  }

  function selectOption(text: string) {
    setAnswers((prev) => ({ ...prev, [question!.id]: text }));
  }

  async function handleNext() {
    if (index < quizSet!.questions.length - 1) {
      setIndex((i) => i + 1);
      return;
    }
    // 마지막 문제 -> 제출
    setSubmitting(true);
    setError(null);
    try {
      await submitQuiz(quizSet!.id, {
        quiz_set_id: quizSet!.id,
        answers: quizSet!.questions.map((q) => ({
          question_id: q.id,
          user_answer: answers[q.id] ?? "",
        })),
      });
      navigate(quizSet!.type === "regenerated" ? `/regenerate/${quizSet!.id}` : `/analysis/${quizSet!.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "제출에 실패했어요.");
    } finally {
      setSubmitting(false);
    }
  }

  const isLast = index === quizSet.questions.length - 1;
  const currentAnswer = answers[question.id];

  return (
    <div className="content quiz-content">
      <div className="quiz-wrap">
        <div className="quiz-meta">
          <div className="quiz-meta-left">
            <b>{materialTitle || "문제 풀이"}</b> · 난이도 {quizSet.difficulty}
          </div>
          <div className="quiz-count">
            <span className="mono">{index + 1}</span> / {quizSet.questions.length}
          </div>
        </div>

        <div className="progress-track">
          {quizSet.questions.map((q, i) => (
            <div key={q.id} className={"progress-seg" + (i <= index || answers[q.id] ? " done" : "")} />
          ))}
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="card quiz-card">
          <div className="concept-tag">
            <TargetIcon size={11} />
            문제 {index + 1}
          </div>

          <p className="question-text">{question.question_text}</p>

          {question.type === "multiple_choice" ? (
            <div className="options">
              {question.options.map((opt, i) => (
                <button
                  key={i}
                  type="button"
                  className={"option-row" + (currentAnswer === opt.option_text ? " selected" : "")}
                  onClick={() => selectOption(opt.option_text)}
                >
                  <span className="option-letter">{String.fromCharCode(65 + i)}</span>
                  <span className="option-radio" />
                  {opt.option_text}
                </button>
              ))}
            </div>
          ) : (
            <input
              className="short-answer-input"
              type="text"
              placeholder="답을 입력하세요"
              value={currentAnswer ?? ""}
              onChange={(e) => selectOption(e.target.value)}
            />
          )}

          <div className="quiz-footer">
            <button className="btn btn-ghost" disabled={index === 0} onClick={() => setIndex((i) => i - 1)}>
              이전
            </button>
            <span className="quiz-count">
              <span className="mono">{answeredCount}</span> / {quizSet.questions.length}문항 응답함
            </span>
            <button className="btn btn-primary" onClick={handleNext} disabled={submitting}>
              {submitting ? "제출 중..." : isLast ? "제출하기" : "다음"}
              {!isLast && <ChevronRightIcon size={13} color="#fff" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
