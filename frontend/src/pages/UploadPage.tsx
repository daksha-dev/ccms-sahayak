import { useMutation } from "@tanstack/react-query";
import type React from "react";
import { useState } from "react";
import { uploadJudgment } from "../api/client";
import { useReviewerStore } from "../store/reviewer";

export function UploadPage({ onReview }: { onReview: () => void }) {
  const setJobId = useReviewerStore((state) => state.setJobId);
  const mutation = useMutation({ mutationFn: uploadJudgment });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  function onFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    // Reset any previous error state
    mutation.reset();
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) return;
    const result = await mutation.mutateAsync(selectedFile);
    setJobId(result.job_id);
    onReview();
  }

  const fileSizeMB = selectedFile ? (selectedFile.size / 1024 / 1024).toFixed(2) : null;

  return (
    <section className="mx-auto max-w-2xl px-4 py-12">
      {/* Hero blurb */}
      <div className="mb-8 text-center">
        <span
          className="inline-flex h-14 w-14 items-center justify-center rounded-2xl text-3xl"
          style={{ background: "#f0d9b0", color: "#c46205" }}
          aria-hidden
        >
          📄
        </span>
        <h2 className="mt-3 text-2xl font-semibold" style={{ color: "#3b2a14" }}>
          Upload a Judgment PDF
        </h2>
        <p className="mt-1 text-sm" style={{ color: "#8a6f4e" }}>
          Karnataka High Court judgments — digital or scanned.
          <br />
          AI will extract fields and generate a verified action plan.
        </p>
      </div>

      {/* Upload card */}
      <form
        className="rounded-2xl border p-8 shadow-card"
        style={{ background: "#fdf8f1", borderColor: "#e2d5bf" }}
        onSubmit={submit}
      >
        {/* Drop-zone */}
        <label
          className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 transition-all duration-150"
          style={{
            borderColor: selectedFile ? "#c46205" : "#d4a55c",
            background: selectedFile ? "#fff3d6" : "#fff8ed",
          }}
        >
          {selectedFile ? (
            /* ── File selected state ─────────────────────────── */
            <>
              <span className="text-4xl" aria-hidden>📎</span>
              <div className="text-center">
                <p className="max-w-xs truncate text-sm font-semibold" style={{ color: "#3b2a14" }}>
                  {selectedFile.name}
                </p>
                <p className="mt-0.5 text-xs" style={{ color: "#8a6f4e" }}>
                  {fileSizeMB} MB · PDF
                </p>
                <p className="mt-2 text-xs font-medium" style={{ color: "#c46205" }}>
                  Click to choose a different file
                </p>
              </div>
            </>
          ) : (
            /* ── Empty state ─────────────────────────────────── */
            <>
              <span className="text-4xl" aria-hidden>⬆️</span>
              <span className="text-sm font-medium" style={{ color: "#6b3c10" }}>
                Click to choose or drag a PDF here
              </span>
            </>
          )}
          <input
            className="hidden"
            name="file"
            type="file"
            accept="application/pdf"
            required
            onChange={onFileChange}
          />
        </label>

        {/* Error */}
        {mutation.error && (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-danger">
            {String((mutation.error as Error).message)}
          </p>
        )}

        {/* Submit */}
        <button
          className="btn btn-primary mt-6 w-full py-2.5 text-base"
          disabled={mutation.isPending || !selectedFile}
        >
          {mutation.isPending ? (
            <span className="flex items-center justify-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Processing…
            </span>
          ) : (
            "Upload and Extract"
          )}
        </button>
      </form>

      {/* Workflow steps */}
      <ol className="mt-8 grid gap-2 text-sm" style={{ color: "#8a6f4e" }}>
        {[
          "PDF text extracted via PyMuPDF; scanned pages sent to Sarvam OCR",
          "Rule + Gemini extraction compared; conflict detection applied",
          "Reviewer approves, edits, or rejects every field",
          "Verified record written to dashboard with bilingual EN/KN summary",
        ].map((step, i) => (
          <li key={i} className="flex items-start gap-3">
            <span
              className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold"
              style={{ background: "#f0d9b0", color: "#c46205" }}
            >
              {i + 1}
            </span>
            {step}
          </li>
        ))}
      </ol>
    </section>
  );
}
