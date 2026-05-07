import { describe, expect, it } from "vitest";
import { actionSummary, daysUntil } from "./dashboard";
import type { DashboardRecord } from "../types";

const record: DashboardRecord = {
  id: 1,
  judgment_id: 1,
  case_number: "WP No. 1 of 2026",
  department: "Revenue",
  urgency_band: "RED",
  appeal_deadline: "2026-05-08",
  action_summary_en: "Comply with order",
  action_summary_kn: "ಕನ್ನಡ ಸಾರಾಂಶ",
  verified_at: "2026-05-01T00:00:00",
  audit_trail: []
};

describe("dashboard helpers", () => {
  it("selects bilingual summaries", () => {
    expect(actionSummary(record, "en")).toBe("Comply with order");
    expect(actionSummary(record, "kn")).toBe("ಕನ್ನಡ ಸಾರಾಂಶ");
  });

  it("calculates appeal countdown", () => {
    expect(daysUntil("2026-05-08", new Date("2026-05-01T00:00:00Z").getTime())).toBe(7);
  });
});
