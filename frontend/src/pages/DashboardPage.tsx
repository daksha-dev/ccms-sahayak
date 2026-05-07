import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { getDashboard, getStats } from "../api/client";
import type { DashboardRecord } from "../types";
import { actionSummary, daysUntil } from "../utils/dashboard";

/* ── Urgency colour helpers ───────────────────────────────────────── */
const URGENCY_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  RED:   { bg: "#fff0f0", text: "#b42318", border: "#f5c6c2" },
  AMBER: { bg: "#fff8ed", text: "#9e4a08", border: "#ffd18a" },
  GREEN: { bg: "#f0faf3", text: "#1a6b38", border: "#b6e5c4" },
};

function urgencyStyle(band: string) {
  return URGENCY_STYLES[band] ?? { bg: "#f8edd8", text: "#3b2a14", border: "#e2d5bf" };
}

export function DashboardPage() {
  const [department, setDepartment] = useState("");
  const [actionType, setActionType] = useState("");
  const [urgency, setUrgency] = useState("");
  const [language, setLanguage] = useState<"en" | "kn">("en");
  const [selected, setSelected] = useState<DashboardRecord | null>(null);

  const params = useMemo(() => {
    const search = new URLSearchParams({ page: "1", limit: "20" });
    if (department) search.set("department", department);
    if (actionType) search.set("action_type", actionType);
    if (urgency) search.set("urgency", urgency);
    return search;
  }, [department, actionType, urgency]);

  const dashboard = useQuery({
    queryKey: ["dashboard", params.toString()],
    queryFn: () => getDashboard(params),
  });
  const stats = useQuery({ queryKey: ["stats"], queryFn: getStats });
  const exportHref = `/api/v1/dashboard/export.csv?${params.toString()}`;

  return (
    <section className="mx-auto max-w-7xl px-4 py-6">

      {/* ── Stat cards ──────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Total active cases"  value={stats.data?.total_active_cases ?? 0} icon="📂" />
        <StatCard label="RED urgency"         value={stats.data?.red_urgency ?? 0}         icon="🔴" accent="#b42318" />
        <StatCard label="AMBER urgency"       value={stats.data?.amber_urgency ?? 0}       icon="🟡" accent="#9e4a08" />
        <StatCard label="Pending appeals"     value={stats.data?.pending_appeals ?? 0}     icon="⚖️" accent="#c46205" />
      </div>

      {/* ── Filters bar ─────────────────────────────────────────── */}
      <div
        className="mt-4 flex flex-wrap items-center gap-2 rounded-xl border p-3"
        style={{ background: "#fdf8f1", borderColor: "#e2d5bf" }}
      >
        <input
          className="rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-saffron-400"
          style={{ borderColor: "#e2d5bf", background: "#fff8ed" }}
          placeholder="Department filter"
          value={department}
          onChange={(e) => setDepartment(e.target.value)}
        />
        <select
          className="rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-saffron-400"
          style={{ borderColor: "#e2d5bf", background: "#fff8ed" }}
          value={actionType}
          onChange={(e) => setActionType(e.target.value)}
        >
          <option value="">All action types</option>
          <option>Compliance</option>
          <option>Appeal</option>
          <option>Cost</option>
          <option>Contempt</option>
          <option>Other</option>
        </select>
        <select
          className="rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-saffron-400"
          style={{ borderColor: "#e2d5bf", background: "#fff8ed" }}
          value={urgency}
          onChange={(e) => setUrgency(e.target.value)}
        >
          <option value="">All urgency</option>
          <option>RED</option>
          <option>AMBER</option>
          <option>GREEN</option>
        </select>

        <div className="ml-auto flex items-center gap-2">
          {(["en", "kn"] as const).map((l) => (
            <button
              key={l}
              className={`btn ${language === l ? "btn-primary" : ""}`}
              onClick={() => setLanguage(l)}
            >
              {l.toUpperCase()}
            </button>
          ))}
          <a
            className="btn"
            href={exportHref}
            style={{ color: "#c46205", borderColor: "#d4a55c" }}
          >
            ↓ CSV
          </a>
        </div>
      </div>

      {/* ── Record list ─────────────────────────────────────────── */}
      <div className="mt-4 grid gap-3">
        {dashboard.isLoading && (
          <p className="text-sm" style={{ color: "#8a6f4e" }}>Loading records…</p>
        )}
        {dashboard.data?.records.length === 0 && (
          <p className="text-sm" style={{ color: "#8a6f4e" }}>No verified records yet.</p>
        )}
        {dashboard.data?.records.map((record) => {
          const days = daysUntil(record.appeal_deadline);
          const us = urgencyStyle(record.urgency_band);
          return (
            <button
              key={record.id}
              className="w-full rounded-xl border p-4 text-left shadow-card transition-shadow hover:shadow-card-active"
              style={{ background: "#fdf8f1", borderColor: "#e2d5bf" }}
              onClick={() => setSelected(record)}
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="font-semibold" style={{ color: "#3b2a14" }}>
                    {record.case_number || "Case number pending"}
                  </h3>
                  <p className="mt-0.5 text-sm" style={{ color: "#8a6f4e" }}>
                    {record.department || "Department pending"}
                  </p>
                </div>
                <span
                  className="shrink-0 rounded-full border px-2.5 py-1 text-xs font-bold"
                  style={{ background: us.bg, color: us.text, borderColor: us.border }}
                >
                  {record.urgency_band}
                </span>
              </div>
              {days !== null && (
                <p className="mt-2 text-sm font-semibold text-danger">
                  ⏰ Appeal countdown: {days} day(s)
                </p>
              )}
              <p className="mt-2 text-sm" style={{ color: "#6b3c10" }}>
                {actionSummary(record, language)}
              </p>
            </button>
          );
        })}
      </div>

      {/* ── Detail drawer ───────────────────────────────────────── */}
      {selected && (
        <div
          className="fixed inset-0 z-50 p-6"
          style={{ background: "rgba(59,42,20,0.45)" }}
          onClick={() => setSelected(null)}
        >
          <div
            className="ml-auto h-full max-w-2xl overflow-auto rounded-2xl p-6 shadow-2xl"
            style={{ background: "#fdf8f1" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4">
              <h2 className="text-lg font-semibold" style={{ color: "#3b2a14" }}>
                {selected.case_number}
              </h2>
              <button className="btn" onClick={() => setSelected(null)}>✕ Close</button>
            </div>
            <p className="mt-3 text-sm" style={{ color: "#6b3c10" }}>
              {actionSummary(selected, language)}
            </p>
            <h3 className="mt-6 font-semibold" style={{ color: "#3b2a14" }}>Audit trail</h3>
            <pre
              className="mt-2 whitespace-pre-wrap rounded-xl p-4 text-xs"
              style={{ background: "#f0d9b0", color: "#3b2a14" }}
            >
              {JSON.stringify(selected.audit_trail, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </section>
  );
}

function StatCard({
  label,
  value,
  icon,
  accent = "#c46205",
}: {
  label: string;
  value: number;
  icon: string;
  accent?: string;
}) {
  return (
    <div
      className="stat-card flex flex-col gap-1"
    >
      <div className="flex items-center gap-2">
        <span className="text-xl" aria-hidden>{icon}</span>
        <p className="text-xs font-medium" style={{ color: "#8a6f4e" }}>{label}</p>
      </div>
      <p className="text-3xl font-bold" style={{ color: accent }}>{value}</p>
    </div>
  );
}
