import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { decideField, getReview, verifyJudgment } from "../api/client";
import { FieldCard } from "../components/FieldCard";
import { PDFViewer } from "../components/PDFViewer";
import { useReviewerStore } from "../store/reviewer";
import type { Decision, ReviewField } from "../types";
import { canSubmitReview, highConfidenceUnreviewed, verifiedCount } from "../utils/reviewer";

export function ReviewPage() {
  const queryClient = useQueryClient();
  const jobId = useReviewerStore((state) => state.jobId);
  const activeFieldId = useReviewerStore((state) => state.activeFieldId);
  const setActiveFieldId = useReviewerStore((state) => state.setActiveFieldId);

  const review = useQuery({
    queryKey: ["review", jobId],
    queryFn: () => getReview(jobId!),
    enabled: Boolean(jobId),
  });

  const decide = useMutation({
    mutationFn: ({
      field,
      decision,
      correctedValue,
      rejectionReason,
    }: {
      field: ReviewField;
      decision: Decision;
      correctedValue?: unknown;
      rejectionReason?: string;
    }) =>
      decideField(jobId!, field.id, {
        decision,
        corrected_value: correctedValue,
        rejection_reason: rejectionReason,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["review", jobId] }),
  });

  const verify = useMutation({ mutationFn: () => verifyJudgment(jobId!) });

  const fields = review.data?.fields ?? [];
  const active = fields.find((f) => f.id === activeFieldId) ?? fields[0];
  const count = verifiedCount(fields);
  const canSubmit = canSubmitReview(fields);
  const highFields = highConfidenceUnreviewed(fields);
  const activeIndex = active ? fields.findIndex((f) => f.id === active.id) : -1;

  async function bulkApproveHigh() {
    for (const field of highFields) {
      await decide.mutateAsync({ field, decision: "APPROVED" });
    }
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const tag = (event.target as HTMLElement).tagName;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(tag)) return;
      if (event.ctrlKey && event.key === "Enter" && canSubmit) {
        verify.mutate();
        return;
      }
      if (!active || !fields.length) return;
      if (event.key === "Tab") {
        event.preventDefault();
        const next = fields[(activeIndex + 1) % fields.length];
        if (next) setActiveFieldId(next.id);
        return;
      }
      if (event.key.toLowerCase() === "a") decide.mutate({ field: active, decision: "APPROVED" });
      if (event.key.toLowerCase() === "e") setActiveFieldId(active.id);
      if (event.key.toLowerCase() === "r")
        decide.mutate({ field: active, decision: "REJECTED", rejectionReason: "wrong extraction" });
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [active, activeIndex, canSubmit, decide, fields, setActiveFieldId, verify]);

  if (!jobId)
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 text-center" style={{ color: "#8a6f4e" }}>
        Upload a judgment before opening the reviewer.
      </div>
    );
  if (review.isLoading)
    return (
      <div className="px-4 py-8 text-sm" style={{ color: "#8a6f4e" }}>
        Loading review…
      </div>
    );
  if (review.error || !review.data || !active)
    return (
      <div className="px-4 py-8 text-sm text-danger">{String(review.error)}</div>
    );

  const pct = fields.length ? Math.round((count / fields.length) * 100) : 0;

  return (
    <section className="mx-auto grid max-w-7xl grid-cols-[minmax(360px,0.9fr)_minmax(520px,1.1fr)] gap-4 px-4 py-4">
      {/* ── Left panel ─────────────────────────────────────────── */}
      <div className="flex flex-col gap-3">
        {/* Header bar */}
        <div
          className="rounded-xl border p-4 shadow-card"
          style={{ background: "#fdf8f1", borderColor: "#e2d5bf" }}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold" style={{ color: "#3b2a14" }}>
                Human Verification
              </h2>
              <p className="mt-0.5 text-xs" style={{ color: "#8a6f4e" }}>
                {count} of {fields.length} fields reviewed
              </p>
              {/* Progress bar */}
              <div
                className="mt-2 h-1.5 w-44 overflow-hidden rounded-full"
                style={{ background: "#e2d5bf" }}
              >
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{ width: `${pct}%`, background: "#c46205" }}
                />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <button
                className="btn text-xs"
                disabled={!highFields.length || decide.isPending}
                onClick={bulkApproveHigh}
              >
                ✓ Bulk approve HIGH
              </button>
              <button
                className="btn btn-primary text-xs"
                disabled={!canSubmit || verify.isPending}
                onClick={() => verify.mutate()}
              >
                {verify.isPending ? (
                  <span className="flex items-center gap-1.5">
                    <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    Submitting…
                  </span>
                ) : (
                  "Submit ⌃↵"
                )}
              </button>
            </div>
          </div>

          {verify.error && (
            <p className="mt-2 text-xs text-danger">{String((verify.error as Error).message)}</p>
          )}

          {/* Keyboard hint */}
          <p className="mt-2 text-xs" style={{ color: "#8a6f4e" }}>
            <kbd className="rounded border px-1 py-0.5 font-mono text-xs" style={{ borderColor: "#d4a55c", color: "#c46205" }}>A</kbd> approve ·{" "}
            <kbd className="rounded border px-1 py-0.5 font-mono text-xs" style={{ borderColor: "#d4a55c", color: "#c46205" }}>E</kbd> edit ·{" "}
            <kbd className="rounded border px-1 py-0.5 font-mono text-xs" style={{ borderColor: "#d4a55c", color: "#c46205" }}>R</kbd> reject ·{" "}
            <kbd className="rounded border px-1 py-0.5 font-mono text-xs" style={{ borderColor: "#d4a55c", color: "#c46205" }}>Tab</kbd> next
          </p>
        </div>

        {/* Field list */}
        <div className="grid max-h-[calc(100vh-260px)] gap-2 overflow-auto pr-1">
          {fields.map((field) => (
            <FieldCard
              key={field.id}
              field={field}
              active={field.id === active.id}
              onFocus={() => setActiveFieldId(field.id)}
              onDecision={(decision, correctedValue, rejectionReason) =>
                decide.mutate({ field, decision, correctedValue, rejectionReason })
              }
            />
          ))}
        </div>
      </div>

      {/* ── Right panel — PDF viewer ─────────────────────────────── */}
      <PDFViewer pdfUrl={review.data.pdf_url} activeField={active} />
    </section>
  );
}
