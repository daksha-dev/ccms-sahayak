import { useState } from "react";
import type { Decision, ReviewField } from "../types";
import { ConfidenceBadge } from "./ConfidenceBadge";

function printable(value: unknown) {
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

const DECISION_STYLE: Record<string, { bg: string; text: string }> = {
  APPROVED: { bg: "#e8f8ee", text: "#1a6b38" },
  EDITED:   { bg: "#fff8ed", text: "#9e4a08" },
  REJECTED: { bg: "#fff0f0", text: "#b42318" },
};

export function FieldCard({
  field,
  active,
  onFocus,
  onDecision,
}: {
  field: ReviewField;
  active: boolean;
  onFocus: () => void;
  onDecision: (decision: Decision, correctedValue?: unknown, rejectionReason?: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(printable(field.extracted_value));
  const [reason, setReason] = useState("wrong extraction");
  const hasDecision = Boolean(field.decision);
  const ds = field.decision ? DECISION_STYLE[field.decision] : null;

  return (
    <section
      className={`field-card ${active ? "shadow-card-active" : ""}`}
      style={active ? { borderColor: "#c46205" } : {}}
      onClick={onFocus}
    >
      {/* Header row */}
      <div className="mb-2 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold" style={{ color: "#3b2a14" }}>
          {field.field_name}
        </h3>
        <div className="flex items-center gap-2">
          {hasDecision && ds && (
            <span
              className="rounded-full border px-2 py-0.5 text-xs font-bold"
              style={{ background: ds.bg, color: ds.text, borderColor: ds.text + "44" }}
            >
              {field.decision}
            </span>
          )}
          <ConfidenceBadge score={field.confidence_score} conflict={field.conflict} />
        </div>
      </div>

      {/* Value area */}
      {editing ? (
        <textarea
          className="min-h-24 w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-saffron-400"
          style={{ borderColor: "#d4a55c", background: "#fff8ed" }}
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      ) : (
        <pre
          className="max-h-32 overflow-auto whitespace-pre-wrap rounded-lg p-2.5 text-xs"
          style={{ background: "#f0d9b0", color: "#3b2a14" }}
        >
          {printable(field.extracted_value)}
        </pre>
      )}

      {/* Action row */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          className="btn text-xs"
          style={{ borderColor: "#b6e5c4", color: "#1a6b38" }}
          onClick={() => onDecision("APPROVED")}
        >
          ✓ Approve
        </button>

        {editing ? (
          <button
            className="btn text-xs"
            style={{ borderColor: "#d4a55c", color: "#c46205" }}
            onClick={() => { onDecision("EDITED", value); setEditing(false); }}
          >
            Save
          </button>
        ) : (
          <button
            className="btn text-xs"
            onClick={() => setEditing(true)}
          >
            ✏ Edit
          </button>
        )}

        <select
          className="rounded-lg border px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-saffron-400"
          style={{ borderColor: "#e2d5bf", background: "#fff8ed" }}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        >
          <option>wrong extraction</option>
          <option>ambiguous</option>
          <option>not applicable</option>
        </select>

        <button
          className="btn text-xs"
          style={{ borderColor: "#f5c6c2", color: "#b42318" }}
          onClick={() => onDecision("REJECTED", undefined, reason)}
        >
          ✕ Reject
        </button>
      </div>
    </section>
  );
}
