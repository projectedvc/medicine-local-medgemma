import type {
  AIAnalysis,
  AnalyticsOverview,
  AuditLog,
  FeedbackType,
  Pathology,
  Report,
  Study,
  User
} from "./types";

const VITE_API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const API_BASE = VITE_API_URL.replace(/\/$/, "") + "/api";

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
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(payload.detail ?? "Ошибка API");
  }
  return response.json() as Promise<T>;
}

async function requestBlob(path: string): Promise<Blob> {
  const headers = new Headers();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE}${path}`, { headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(payload.detail ?? "Ошибка API");
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

  runAI: (studyId: number, wait = true, auto = false) =>
    request<AIAnalysis>(`/studies/${studyId}/ai/run`, {
      method: "POST",
      body: JSON.stringify({ wait, auto })
    }),

  listAI: (studyId: number) => request<AIAnalysis[]>(`/studies/${studyId}/ai`),

  getReport: (studyId: number) => request<Report>(`/studies/${studyId}/report`),

  createDraft: (studyId: number) => request<Report>(`/studies/${studyId}/report/draft`, { method: "POST" }),

  saveReport: (studyId: number, final_text: string) =>
    request<Report>(`/studies/${studyId}/report`, { method: "PUT", body: JSON.stringify({ final_text }) }),

  confirmReport: (studyId: number) =>
    request<Report>(`/studies/${studyId}/report/confirm`, {
      method: "POST",
      body: JSON.stringify({ accept_responsibility: true })
    }),

  exportReport: (studyId: number, format: "pdf" | "docx") => requestBlob(`/studies/${studyId}/report/export/${format}`),

  listPathologies: () => request<Pathology[]>("/pathologies"),

  sendFeedback: (studyId: number, payload: { analysis_id?: number; feedback_type: FeedbackType; comment?: string }) =>
    request(`/studies/${studyId}/feedback`, { method: "POST", body: JSON.stringify(payload) }),

  audit: () => request<AuditLog[]>("/audit?limit=100"),

  analytics: () => request<AnalyticsOverview>("/analytics/overview")
};

export function currentToken() {
  return token;
}
