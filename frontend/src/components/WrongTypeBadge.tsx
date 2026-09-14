import type { WrongAnswerTagType } from "../api/types";
import { ZapIcon, ShuffleIcon, QuestionIcon } from "./Icons";

export const WRONG_TYPE_CONFIG: Record<
  WrongAnswerTagType,
  { label: string; cls: string; icon: typeof ZapIcon }
> = {
  careless_mistake: { label: "단순 실수", cls: "badge-warning", icon: ZapIcon },
  concept_confusion: { label: "개념 혼동", cls: "badge-serious", icon: ShuffleIcon },
  not_learned: { label: "미학습", cls: "badge-critical", icon: QuestionIcon },
};

export default function WrongTypeBadge({ type }: { type: WrongAnswerTagType }) {
  const cfg = WRONG_TYPE_CONFIG[type];
  if (!cfg) return null;
  const Icon = cfg.icon;
  return (
    <span className={`badge ${cfg.cls}`}>
      <Icon size={11} />
      {cfg.label}
    </span>
  );
}

export const WRONG_TYPE_LABEL: Record<WrongAnswerTagType, string> = {
  careless_mistake: "단순 실수",
  concept_confusion: "개념 혼동",
  not_learned: "미학습",
};
