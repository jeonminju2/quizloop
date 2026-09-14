import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listMaterials, uploadMaterial, updateMaterial, generateQuiz, ApiError } from "../api/client";
import type { Material } from "../api/types";
import StatTile from "../components/StatTile";
import { UploadIcon, FileIcon, CheckIcon, ClockIcon } from "../components/Icons";
import "./MaterialsPage.css";

const ACCEPTED = [".pdf", ".ppt", ".pptx"];

function fileExtLabel(fileType: string) {
  const ft = fileType.toLowerCase();
  if (ft.includes("ppt")) return "PPT";
  return "PDF";
}

function statusView(status: string) {
  switch (status) {
    case "ready":
      return { cls: "badge-good", label: "완료", icon: CheckIcon };
    case "uploaded":
    case "processing":
      return { cls: "badge-warning", label: "분석 중", icon: ClockIcon };
    case "failed":
      return { cls: "badge-critical", label: "실패", icon: ClockIcon };
    default:
      return { cls: "badge-muted", label: status, icon: ClockIcon };
  }
}

export default function MaterialsPage() {
  const navigate = useNavigate();
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const [styleNoteDraft, setStyleNoteDraft] = useState("");
  const [editingStyleId, setEditingStyleId] = useState<string | null>(null);
  const [styleEditValue, setStyleEditValue] = useState("");
  const [savingStyleId, setSavingStyleId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setMaterials(await listMaterials());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "자료 목록을 불러오지 못했어요.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // 백그라운드 큐(worker.py)가 자료를 처리하는 동안엔 status가 uploaded/processing으로 남아있으니,
  // 그런 자료가 하나라도 있으면 몇 초마다 조용히 다시 불러와서 "완료"로 바뀌는 걸 감지한다.
  const refreshSilently = useCallback(async () => {
    try {
      setMaterials(await listMaterials());
    } catch {
      // 폴링 중 에러는 조용히 무시 — 다음 주기에 다시 시도
    }
  }, []);

  useEffect(() => {
    const hasPending = materials.some((m) => m.status === "uploaded" || m.status === "processing");
    if (!hasPending) return;
    const intervalId = setInterval(refreshSilently, 3000);
    return () => clearInterval(intervalId);
  }, [materials, refreshSilently]);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    const file = files[0];
    const ok = ACCEPTED.some((ext) => file.name.toLowerCase().endsWith(ext));
    if (!ok) {
      setError("PDF 또는 PPTX 파일만 업로드할 수 있어요.");
      return;
    }
    setUploading(true);
    setError(null);
    try {
      await uploadMaterial(file, styleNoteDraft);
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "업로드에 실패했어요.");
    } finally {
      setUploading(false);
    }
  }

  function startEditStyle(material: Material) {
    setEditingStyleId(material.id);
    setStyleEditValue(material.exam_style_note ?? "");
  }

  async function saveStyleNote(materialId: string) {
    setSavingStyleId(materialId);
    setError(null);
    try {
      const updated = await updateMaterial(materialId, { exam_style_note: styleEditValue });
      setMaterials((prev) => prev.map((m) => (m.id === materialId ? updated : m)));
      setEditingStyleId(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "시험 스타일 메모 저장에 실패했어요.");
    } finally {
      setSavingStyleId(null);
    }
  }

  async function handleGenerate(material: Material) {
    setGeneratingId(material.id);
    setError(null);
    try {
      const quizSet = await generateQuiz({ material_id: material.id, num_questions: 10 });
      localStorage.setItem("quizloop:currentQuizSetId", quizSet.id);
      localStorage.setItem("quizloop:currentMaterialTitle", material.title);
      navigate(`/quiz/${quizSet.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "문제 생성에 실패했어요.");
    } finally {
      setGeneratingId(null);
    }
  }

  const readyCount = materials.filter((m) => m.status === "ready").length;

  return (
    <div className="content">
      <div className="page-header">
        <div>
          <div className="eyebrow">자료 관리</div>
          <h1>강의자료</h1>
          <p className="subtitle">PDF·PPT를 업로드하면 자료 안에서만 근거를 찾아 문제를 만들어요.</p>
        </div>
        <label className="btn btn-primary" style={{ cursor: "pointer" }}>
          <UploadIcon size={14} color="#fff" />
          {uploading ? "업로드 중..." : "자료 업로드"}
          <input
            type="file"
            accept={ACCEPTED.join(",")}
            onChange={(e) => handleFiles(e.target.files)}
            disabled={uploading}
          />
        </label>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="style-note-block">
        <label className="style-note-label" htmlFor="exam-style-note">
          교수님 시험 스타일 (선택) — 다음에 업로드할 자료에 적용돼요
        </label>
        <textarea
          id="exam-style-note"
          className="style-note-input"
          rows={2}
          placeholder="예: 객관식 위주, 지엽적인 것보다 핵심 정의 위주로 출제, 사례 응용문제 자주 나옴"
          value={styleNoteDraft}
          onChange={(e) => setStyleNoteDraft(e.target.value)}
        />
      </div>

      <div className="stat-grid">
        <StatTile label="업로드한 자료" value={materials.length} unit="개" />
        <StatTile label="분석 완료" value={readyCount} unit="개" />
        <StatTile label="분석 중" value={materials.length - readyCount} unit="개" />
      </div>

      <div
        className={"dropzone" + (dragging ? " dragging" : "")}
        onClick={(e) => (e.currentTarget.querySelector("input") as HTMLInputElement)?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
      >
        <div className="dropzone-icon">
          <UploadIcon size={22} />
        </div>
        <div className="dropzone-title">파일을 드래그하거나 클릭해서 업로드</div>
        <div className="dropzone-sub">PDF, PPTX · 자료 1개당 최대 50MB</div>
        <input type="file" accept={ACCEPTED.join(",")} onChange={(e) => handleFiles(e.target.files)} />
      </div>

      <div className="section-title">업로드한 자료</div>

      {loading ? (
        <div className="empty-state">불러오는 중...</div>
      ) : materials.length === 0 ? (
        <div className="empty-state">아직 업로드한 자료가 없어요. 위에서 첫 자료를 올려보세요.</div>
      ) : (
        <div className="material-list">
          {materials.map((m) => {
            const sv = statusView(m.status);
            const StatusIcon = sv.icon;
            const isReady = m.status === "ready";
            const isEditingStyle = editingStyleId === m.id;
            return (
              <div className="material-row-wrap" key={m.id}>
                <div className="material-row">
                  <div className="file-icon">
                    <FileIcon size={18} />
                    <span className="file-chip">{fileExtLabel(m.file_type)}</span>
                  </div>
                  <div className="material-info">
                    <div className="material-title">{m.title}</div>
                    <div className="material-meta">
                      {isReady ? "분석 완료" : "개념 분석 중"}
                      {m.exam_style_note ? ` · 시험 스타일 메모 있음` : ""}
                    </div>
                  </div>
                  <span className={`badge ${sv.cls}`}>
                    <StatusIcon size={11} />
                    {sv.label}
                  </span>
                  <button className="btn btn-ghost small" onClick={() => startEditStyle(m)}>
                    시험 스타일
                  </button>
                  <button
                    className="btn btn-ghost small"
                    disabled={!isReady || generatingId === m.id}
                    onClick={() => handleGenerate(m)}
                  >
                    {generatingId === m.id ? "생성 중..." : "문제 생성"}
                  </button>
                </div>
                {isEditingStyle && (
                  <div className="style-note-editor">
                    <textarea
                      className="style-note-input"
                      rows={2}
                      placeholder="예: 객관식 위주, 지엽적인 것보다 핵심 정의 위주로 출제, 사례 응용문제 자주 나옴"
                      value={styleEditValue}
                      onChange={(e) => setStyleEditValue(e.target.value)}
                    />
                    <div className="style-note-actions">
                      <button
                        className="btn btn-ghost small"
                        onClick={() => setEditingStyleId(null)}
                        disabled={savingStyleId === m.id}
                      >
                        취소
                      </button>
                      <button
                        className="btn btn-primary small"
                        onClick={() => saveStyleNote(m.id)}
                        disabled={savingStyleId === m.id}
                      >
                        {savingStyleId === m.id ? "저장 중..." : "저장"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
