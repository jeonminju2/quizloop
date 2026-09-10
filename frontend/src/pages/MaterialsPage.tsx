import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listMaterials, uploadMaterial, generateQuiz, ApiError } from "../api/client";
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
      await uploadMaterial(file);
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "업로드에 실패했어요.");
    } finally {
      setUploading(false);
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
            return (
              <div className="material-row" key={m.id}>
                <div className="file-icon">
                  <FileIcon size={18} />
                  <span className="file-chip">{fileExtLabel(m.file_type)}</span>
                </div>
                <div className="material-info">
                  <div className="material-title">{m.title}</div>
                  <div className="material-meta">{isReady ? "분석 완료" : "개념 분석 중"}</div>
                </div>
                <span className={`badge ${sv.cls}`}>
                  <StatusIcon size={11} />
                  {sv.label}
                </span>
                <button
                  className="btn btn-ghost small"
                  disabled={!isReady || generatingId === m.id}
                  onClick={() => handleGenerate(m)}
                >
                  {generatingId === m.id ? "생성 중..." : "문제 생성"}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
