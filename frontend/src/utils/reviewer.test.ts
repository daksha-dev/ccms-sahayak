import { describe, expect, it } from "vitest";
import { canSubmitReview, highConfidenceUnreviewed, verifiedCount } from "./reviewer";
import type { ReviewField } from "../types";

const fields: ReviewField[] = [
  { id: 1, field_name: "case_number", extracted_value: "WP", confidence_score: 0.9, source_page: 1, source_bbox: null, extraction_source: "BOTH", conflict: false, decision: "APPROVED" },
  { id: 2, field_name: "directives", extracted_value: [], confidence_score: 0.35, source_page: null, source_bbox: null, extraction_source: "CONFLICT", conflict: true, decision: null }
];

describe("reviewer helpers", () => {
  it("counts decisions and locks submit until every field is reviewed", () => {
    expect(verifiedCount(fields)).toBe(1);
    expect(canSubmitReview(fields)).toBe(false);
    expect(canSubmitReview(fields.map((field) => ({ ...field, decision: "APPROVED" })))).toBe(true);
  });

  it("bulk approval excludes conflicts and already reviewed fields", () => {
    expect(highConfidenceUnreviewed(fields)).toHaveLength(0);
    expect(highConfidenceUnreviewed([{ ...fields[0], decision: null }])).toHaveLength(1);
  });
});
