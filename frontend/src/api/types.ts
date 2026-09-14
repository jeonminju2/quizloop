// backend/app/schemas.py 를 그대로 옮긴 타입들. 스키마를 고치면 여기도 같이 고칠 것.

// ---------- Auth ----------

export interface SignupRequest {
  email: string;
  password: string;
  name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenOut {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  name?: string | null;
}

export type MaterialStatus = "uploaded" | "processing" | "ready" | "failed";

export interface Material {
  id: string;
  title: string;
  file_type: string;
  status: string;
  exam_style_note?: string | null;
}

export interface MaterialUpdate {
  exam_style_note?: string | null;
}

export type QuestionType = "multiple_choice" | "short_answer";
export type Difficulty = "easy" | "medium" | "hard";

export interface QuizGenerateRequest {
  material_id: string;
  num_questions?: number;
  difficulty?: Difficulty;
  question_types?: QuestionType[];
  concept_ids?: string[];
}

export interface QuestionOption {
  option_text: string;
  option_order: number;
}

export interface Question {
  id: string;
  type: QuestionType;
  question_text: string;
  options: QuestionOption[];
}

export interface QuizSet {
  id: string;
  type: "initial" | "regenerated";
  difficulty: Difficulty;
  material_id: string;
  source_quiz_set_id: string | null;
  questions: Question[];
}

export interface AnswerIn {
  question_id: string;
  user_answer: string;
}

export interface SubmissionCreate {
  quiz_set_id: string;
  answers: AnswerIn[];
}

export type WrongAnswerTagType = "careless_mistake" | "concept_confusion" | "not_learned";

export interface WrongAnswerTag {
  tag_type: WrongAnswerTagType;
  reasoning?: string | null;
}

export interface SubmissionAnswer {
  question_id: string;
  user_answer: string;
  is_correct: boolean;
  wrong_tag?: WrongAnswerTag | null;
}

export interface Submission {
  id: string;
  score: number;
  answers: SubmissionAnswer[];
}

export interface RegenerateRequest {
  source_quiz_set_id: string;
  num_questions?: number;
}

export interface ConceptAccuracy {
  concept_id: string;
  concept_name: string;
  correct: number;
  total: number;
  accuracy: number;
}

export interface TypeBreakdownItem {
  tag_type: WrongAnswerTagType;
  count: number;
  pct: number;
}

export interface AnalysisDetail {
  question_id: string;
  question_text: string;
  user_answer: string;
  correct_answer: string;
  tag_type: WrongAnswerTagType | null;
  source_label: string | null;
}

export interface QuizAnalysis {
  quiz_set_id: string;
  submission_id: string;
  total: number;
  correct: number;
  accuracy: number;
  concept_accuracy: ConceptAccuracy[];
  type_breakdown: TypeBreakdownItem[];
  details: AnalysisDetail[];
}
