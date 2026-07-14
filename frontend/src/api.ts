import type {
  AIAnalysis,
  AnalyticsOverview,
  AssistantMessage,
  AuditLog,
  CRMRecord,
  FeedbackType,
  Pathology,
  Report,
  Study,
  User
} from "./types";

function isLocalHost() {
  return ["localhost", "127.0.0.1", "0.0.0.0", ""].includes(window.location.hostname);
}

const DEFAULT_API_URL = import.meta.env.DEV && isLocalHost() ? "http://127.0.0.1:8000" : "";
const CONFIGURED_API_URL = import.meta.env.DEV ? import.meta.env.VITE_API_URL : undefined;

function createApiBase(rawUrl: string | undefined) {
  const cleaned = (rawUrl || DEFAULT_API_URL).trim().replace(/\/+$/, "");
  if (!cleaned) return "/api";
  return cleaned.endsWith("/api") ? cleaned : `${cleaned}/api`;
}

const API_BASE = createApiBase(CONFIGURED_API_URL);
const USES_NGROK = API_BASE === "/api" || /\.ngrok(-free)?\./.test(API_BASE);

let token = localStorage.getItem("medicine_token") ?? "";

export function setAuthToken(nextToken: string) {
  token = nextToken;
  if (nextToken) {
    localStorage.setItem("medicine_token", nextToken);
  } else {
    localStorage.removeItem("medicine_token");
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (USES_NGROK) {
    headers.set("ngrok-skip-browser-warning", "true");
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    const detail = typeof payload.detail === "string" ? payload.detail : response.statusText;
    throw new Error(`${detail || "Ошибка API"} (${response.status})`);
  }
  return response.json() as Promise<T>;
}

async function requestBlob(path: string): Promise<Blob> {
  const headers = new Headers();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (USES_NGROK) {
    headers.set("ngrok-skip-browser-warning", "true");
  }
  const response = await fetch(`${API_BASE}${path}`, { headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    const detail = typeof payload.detail === "string" ? payload.detail : response.statusText;
    throw new Error(`${detail || "Ошибка API"} (${response.status})`);
  }
  return response.blob();
}

export const api = {
  login: (login: string, password: string) =>
    request<{ access_token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ login, password })
    }),

  me: () => request<User>("/users/me"),

  listUsers: () => request<User[]>("/users"),

  listDoctors: () => request<User[]>("/users/doctors"),

  listStudies: (params: Record<string, string>) => {
    const query = new URLSearchParams(params);
    return request<Study[]>(`/studies${query.toString() ? `?${query}` : ""}`);
  },

  createStudy: (payload: { patient_code: string; study_type: string; clinical_note?: string }) =>
    request<Study>("/studies", { method: "POST", body: JSON.stringify(payload) }),

  uploadImage: (studyId: number, file: File) => {
    const data = new FormData();
    data.append("file", file);
    return request<Study>(`/studies/${studyId}/upload`, { method: "POST", body: data });
  },

  getStudy: (studyId: number) => request<Study>(`/studies/${studyId}`),

  previewImage: (studyId: number) => requestBlob(`/studies/${studyId}/image/preview`),

  runAI: (studyId: number, wait = true, auto = false, lang = "ru", modelVariant: "base" | "pneumonia_v1" = "base") =>
    request<AIAnalysis>(`/studies/${studyId}/ai/run`, {
      method: "POST",
      body: JSON.stringify({ wait, auto, lang, model_variant: modelVariant })
    }),

  listAI: (studyId: number) => request<AIAnalysis[]>(`/studies/${studyId}/ai`),

  getReport: (studyId: number, lang = "ru") => request<Report>(`/studies/${studyId}/report?lang=${encodeURIComponent(lang)}`),

  createDraft: (studyId: number, lang = "ru") =>
    request<Report>(`/studies/${studyId}/report/draft?lang=${encodeURIComponent(lang)}`, { method: "POST" }),

  saveReport: (studyId: number, final_text: string) =>
    request<Report>(`/studies/${studyId}/report`, { method: "PUT", body: JSON.stringify({ final_text }) }),

  confirmReport: (studyId: number) =>
    request<Report>(`/studies/${studyId}/report/confirm`, {
      method: "POST",
      body: JSON.stringify({ accept_responsibility: true })
    }),

  exportReport: (studyId: number, format: "pdf" | "docx", lang = "ru") =>
    requestBlob(`/studies/${studyId}/report/export/${format}?lang=${encodeURIComponent(lang)}`),

  listPathologies: () => request<Pathology[]>("/pathologies"),

  sendFeedback: (studyId: number, payload: { analysis_id?: number; feedback_type: FeedbackType; comment?: string }) =>
    request(`/studies/${studyId}/feedback`, { method: "POST", body: JSON.stringify(payload) }),

  audit: () => request<AuditLog[]>("/audit?limit=100"),

  analytics: () => request<AnalyticsOverview>("/analytics/overview"),

  listCrm: (params: Record<string, string> = {}) => {
    const query = new URLSearchParams(params);
    return request<CRMRecord[]>(`/crm${query.toString() ? `?${query}` : ""}`);
  },

  createCrm: (payload: {
    patient_code: string;
    contact_type: string;
    status: string;
    priority: string;
    summary: string;
    note: string;
    next_step?: string | null;
    due_at?: string | null;
    participant_ids?: number[];
    linked_study_ids?: number[];
  }) => request<CRMRecord>("/crm", { method: "POST", body: JSON.stringify(payload) }),

  updateCrm: (
    recordId: number,
    payload: Partial<{
      patient_code: string;
      contact_type: string;
      status: string;
      priority: string;
      summary: string;
      note: string;
      next_step: string | null;
      due_at: string | null;
      participant_ids: number[];
      linked_study_ids: number[];
    }>
  ) => request<CRMRecord>(`/crm/${recordId}`, { method: "PATCH", body: JSON.stringify(payload) }),

  addCrmActivity: (recordId: number, content: string, activity_type = "note") =>
    request(`/crm/${recordId}/activities`, {
      method: "POST",
      body: JSON.stringify({ content, activity_type })
    }),

  chatAssistant: (messages: AssistantMessage[], lang: "kk" | "ru" | "en", study_id?: number) =>
    request<{ message: string }>("/assistant/chat", {
      method: "POST",
      body: JSON.stringify({ messages, lang, study_id })
    }),

  deleteCrm: (recordId: number) =>
    fetch(`${API_BASE}/crm/${recordId}`, {
      method: "DELETE",
      headers: (() => {
        const headers = new Headers();
        if (token) headers.set("Authorization", `Bearer ${token}`);
        if (USES_NGROK) headers.set("ngrok-skip-browser-warning", "true");
        return headers;
      })()
    }).then((response) => {
      if (!response.ok) throw new Error(`Ошибка API (${response.status})`);
    })
};

export function currentToken() {
  return token;
}
