import type { DashboardRecord, DashboardStats, Decision, ReviewResponse } from "../types";

const jsonHeaders = { "Content-Type": "application/json" };

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  return response.json() as Promise<T>;
}

export async function uploadJudgment(file: File): Promise<{ job_id: number }> {
  const data = new FormData();
  data.append("file", file);
  return parse(await fetch("/api/v1/judgments/upload", { method: "POST", body: data }));
}

export async function getReview(jobId: number): Promise<ReviewResponse> {
  return parse(await fetch(`/api/v1/judgments/${jobId}/review`));
}

export async function decideField(jobId: number, fieldId: number, body: { decision: Decision; corrected_value?: unknown; rejection_reason?: string }) {
  return parse(await fetch(`/api/v1/judgments/${jobId}/fields/${fieldId}`, { method: "PATCH", headers: jsonHeaders, body: JSON.stringify(body) }));
}

export async function verifyJudgment(jobId: number) {
  return parse(await fetch(`/api/v1/judgments/${jobId}/verify`, { method: "POST" }));
}

export async function getDashboard(params: URLSearchParams): Promise<{ records: DashboardRecord[]; total: number }> {
  return parse(await fetch(`/api/v1/dashboard?${params.toString()}`));
}

export async function getStats(): Promise<DashboardStats> {
  return parse(await fetch("/api/v1/dashboard/stats"));
}
