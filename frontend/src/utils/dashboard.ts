import type { DashboardRecord } from "../types";

export function actionSummary(record: DashboardRecord, language: "en" | "kn") {
  return language === "kn" ? record.action_summary_kn || record.action_summary_en : record.action_summary_en;
}

export function daysUntil(dateValue: string | null, now = Date.now()) {
  if (!dateValue) return null;
  const ms = new Date(dateValue).getTime() - now;
  return Math.ceil(ms / 86400000);
}
