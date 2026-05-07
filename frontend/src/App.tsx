import { useEffect, useState } from "react";
import { DashboardPage } from "./pages/DashboardPage";
import { ReviewPage } from "./pages/ReviewPage";
import { UploadPage } from "./pages/UploadPage";
import { useReviewerStore } from "./store/reviewer";

type Route = "upload" | "review" | "dashboard";

export function App() {
  const [route, setRouteState] = useState<Route>(
    (new URLSearchParams(window.location.search).get("view") as Route | null) ?? "upload"
  );
  const jobId = useReviewerStore((state) => state.jobId);

  useEffect(() => {
    const sync = () =>
      setRouteState(
        (new URLSearchParams(window.location.search).get("view") as Route | null) ?? "upload"
      );
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);

  const setRoute = (next: Route) => {
    const url = new URL(window.location.href);
    url.searchParams.set("view", next);
    window.history.pushState({}, "", url);
    setRouteState(next);
  };

  return (
    <main className="min-h-screen" style={{ background: "#fdf3e3" }}>
      {/* ── Header ─────────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-40 border-b"
        style={{
          background: "linear-gradient(90deg, #3b2a14 0%, #6b3c10 100%)",
          borderColor: "#5a3010",
        }}
      >
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3">
          {/* Logo / title */}
          <div className="flex items-center gap-3">
            {/* Saffron diamond icon */}
            <span
              className="flex h-8 w-8 items-center justify-center rounded-lg text-lg font-bold"
              style={{ background: "#f59519", color: "#3b2a14" }}
              aria-hidden
            >
              ⚖
            </span>
            <div>
              <h1 className="text-base font-semibold leading-none" style={{ color: "#fdf3e3" }}>
                CCMS-Sahayak
              </h1>
              <p className="text-xs" style={{ color: "#d4a55c" }}>
                From Court Judgments to Verified Action Plans
              </p>
            </div>
          </div>

          {/* Nav tabs */}
          <nav className="flex gap-1">
            {(["upload", "review", "dashboard"] as Route[]).map((r) => {
              const labels: Record<Route, string> = {
                upload: "Upload",
                review: "Review",
                dashboard: "Dashboard",
              };
              const isActive = route === r;
              const isDisabled = r === "review" && !jobId;
              return (
                <button
                  key={r}
                  disabled={isDisabled}
                  onClick={() => setRoute(r)}
                  className="rounded-lg px-4 py-1.5 text-sm font-medium transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-40"
                  style={{
                    background: isActive ? "#f59519" : "transparent",
                    color: isActive ? "#3b2a14" : "#f0d9b0",
                    boxShadow: isActive ? "0 1px 4px rgba(0,0,0,0.25)" : "none",
                  }}
                >
                  {labels[r]}
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* ── Pages ──────────────────────────────────────────────── */}
      {route === "upload"    && <UploadPage onReview={() => setRoute("review")} />}
      {route === "review"    && <ReviewPage />}
      {route === "dashboard" && <DashboardPage />}
    </main>
  );
}
