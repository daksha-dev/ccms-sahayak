import type { ReviewField } from "../types";

export function verifiedCount(fields: ReviewField[]) {
  return fields.filter((field) => field.decision).length;
}

export function canSubmitReview(fields: ReviewField[]) {
  return fields.length > 0 && verifiedCount(fields) === fields.length;
}

export function highConfidenceUnreviewed(fields: ReviewField[]) {
  return fields.filter((field) => field.confidence_score >= 0.85 && !field.conflict && !field.decision);
}
