export type Role = "admin" | "radiologist" | "physician" | "expert" | "student" | "analyst";

export type StudyStatus =
  | "created"
  | "uploaded"
  | "checked"
  | "ready_for_analysis"
  | "analyzing"
  | "ai_completed"
  | "draft_ready"
  | "confirmed"
  | "exported"
  | "failed";

export type AIJobStatus = "queued" | "running" | "completed" | "failed";

export type FindingClass = "normal" | "pneumonia" | "pleural_effusion" | "pneumothorax" | "atelectasis";

export type FeedbackType = "false_positive" | "false_negative" | "wrong_region" | "other";

export interface User {
  id: number;
  login: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface ImageFile {
  id: number;
  original_filename: string;
  content_type: string | null;
  size_bytes: number;
  file_format: string;
  width: number | null;
  height: number | null;
  validation_status: string;
  validation_message: string;
  created_at: string;
}

export interface Study {
  id: number;
  accession_number: string;
  patient_code: string;
  study_type: string;
  clinical_note: string | null;
  status: StudyStatus;
  created_at: string;
  updated_at: string;
  uploader: User;
  assigned_radiologist: User | null;
  images?: ImageFile[];
}

export interface AIAnalysis {
  id: number;
  study_id: number;
  status: AIJobStatus;
  predicted_class: FindingClass | null;
  raw_predicted_label: string | null;
  confidence: number | null;
  threshold: number;
  hidden_due_low_confidence: boolean;
  warning: string | null;
  probabilities_json: string | null;
  heatmap_path: string | null;
  model_version: string;
  dataset_version: string;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  disclaimer: string;
}

export interface Report {
  id: number;
  study_id: number;
  ai_draft_text: string | null;
  ai_draft_created_at: string | null;
  final_text: string | null;
  edited_by: User | null;
  confirmed_by: User | null;
  confirmed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Pathology {
  id: number;
  slug: string;
  title: string;
  signs: string;
  report_template: string;
  examples: string | null;
  references: string | null;
  updated_at: string;
}

export interface AuditLog {
  id: number;
  user: User | null;
  action: string;
  entity_type: string | null;
  entity_id: number | null;
  details_json: string | null;
  ip_address: string | null;
  created_at: string;
}

export interface AnalyticsOverview {
  studies_by_status: Record<string, number>;
  studies_total: number;
  ai_completed: number;
  ai_failed: number;
  ai_average_confidence: number | null;
  feedback_by_type: Record<string, number>;
}
