// LOCATION: app/(dashboard)/dashboard/page.tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import {
  getDashboardStudyPlan,
  getDashboardHeatmap,
  getProfileInfo,
  getRecommendations,
  type DashboardStudyPlan,
  type DashboardHeatmap,
  type RecommendationsResponse,
  type RecommendationPriority,
} from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ProfileSnippet {
  name: string;
  email: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

// 5-step emerald scale, evenly spaced so the legend and grid always agree.
function getCellIntensity(count: number): string {
  if (count === 0) return "bg-white/[0.06] border border-white/[0.07]";
  if (count <= 2)  return "bg-emerald-900 border border-emerald-800/60";
  if (count <= 4)  return "bg-emerald-700 border border-emerald-600/50";
  if (count <= 6)  return "bg-emerald-500 border border-emerald-400/40";
  return                  "bg-emerald-300 border border-emerald-200/60 shadow-[0_0_6px_rgba(110,231,183,0.45)]";
}

// Build a full-year (Jan 1 → Dec 31) grid from the activity map, grouped by
// week. Each week is a column of 7 day cells, GitHub-style. The first and
// last columns are padded with empty (non-rendering) slots so every column
// still has 7 rows, but those padding slots carry no date and are never
// considered when building month labels or handling hover/click — this is
// what guarantees the year boundary can never produce a duplicate or
// colliding month label.
function buildWeekColumns(
  activity: Record<string, number>,
  year: number
): Array<Array<{ date: string; count: number } | null>> {
  const jan1 = new Date(year, 0, 1);
  const dec31 = new Date(year, 11, 31);

  const startDow = (jan1.getDay() + 6) % 7; // Mon=0 … Sun=6
  const gridStart = new Date(jan1);
  gridStart.setDate(jan1.getDate() - startDow);

  const endDow = (dec31.getDay() + 6) % 7;
  const gridEnd = new Date(dec31);
  gridEnd.setDate(dec31.getDate() + (6 - endDow));

  const totalDays = Math.round((gridEnd.getTime() - gridStart.getTime()) / 86400000) + 1;
  const totalWeeks = Math.ceil(totalDays / 7);

  const weeks: Array<Array<{ date: string; count: number } | null>> = [];

  for (let w = 0; w < totalWeeks; w++) {
    const col: Array<{ date: string; count: number } | null> = [];
    for (let d = 0; d < 7; d++) {
      const cell = new Date(gridStart);
      cell.setDate(gridStart.getDate() + w * 7 + d);
      if (cell.getFullYear() !== year) {
        col.push(null); // padding slot — never labeled, never interactive
        continue;
      }
      const key = cell.toISOString().slice(0, 10);
      col.push({ date: key, count: activity[key] ?? 0 });
    }
    weeks.push(col);
  }
  return weeks;
}

const MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

// Label the first column in which each month appears. Padding columns
// (all-null, from the partial week before Jan 1 or after Dec 31) are
// skipped outright, so the year boundary can never emit a label at all —
// there is nothing left for "Dec" to attach to once December's real cells
// are exhausted.
function monthLabelsRow(
  weeks: Array<Array<{ date: string; count: number } | null>>
) {
  const labels: Array<{ label: string; col: number }> = [];
  let lastMonth = -1;
  weeks.forEach((col, i) => {
    const firstRealCell = col.find((c): c is { date: string; count: number } => c !== null);
    if (!firstRealCell) return; // entire column is padding
    const m = new Date(firstRealCell.date + "T00:00:00").getMonth();
    if (m !== lastMonth) {
      labels.push({ label: MONTH_LABELS[m], col: i });
      lastMonth = m;
    }
  });
  return labels;
}

function formatLongDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function priorityBadgeClass(priority: RecommendationPriority): string {
  if (priority === "high") return "border-red-500/30 bg-red-500/10 text-red-300";
  if (priority === "medium") return "border-yellow-500/30 bg-yellow-500/10 text-yellow-300";
  return "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";
}

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 5)  return "Burning the midnight oil";
  if (h < 12) return "Good Morning";
  if (h < 17) return "Good Afternoon";
  if (h < 21) return "Good Evening";
  return "Good Evening";
}

// ── Layout constants (kept in one place so grid math & label math agree) ────
const CELL = 15;      // cell width/height in px
const GAP = 4;         // gap between cells in px
const COL_STEP = CELL + GAP; // px advance per week column

// ── Component ─────────────────────────────────────────────────────────────────

export default function Dashboard() {
  useAuth();

  const [plan,    setPlan]    = useState<DashboardStudyPlan | null>(null);
  const [heatmap, setHeatmap] = useState<DashboardHeatmap   | null>(null);
  const [profile, setProfile] = useState<ProfileSnippet     | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(false);
  const [hoveredCell, setHoveredCell] = useState<{ date: string; count: number } | null>(null);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [planData, heatData, profileData, recommendationData] = await Promise.all([
        getDashboardStudyPlan(),
        getDashboardHeatmap(),
        getProfileInfo(),
        getRecommendations(),
      ]);
      setPlan(planData);
      setHeatmap(heatData);
      setRecommendations(recommendationData);
      // Profile is supplementary (greeting only) — a missing/odd shape here
      // should never block the rest of the dashboard from rendering.
      if (profileData && !profileData.detail) {
        setProfile({ name: profileData.name ?? "", email: profileData.email ?? "" });
      }
    } catch (err) {
      console.error("Dashboard error:", err);
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch once on mount only. No polling, no refetch-on-focus — the
  // dashboard loads once and stays put until the page is reloaded.
  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  // ── Loading ────────────────────────────────────────────────────────────────
  if (loading) return (
    <div className="min-h-screen bg-[#060d1f] p-8 flex items-center gap-3 text-slate-400 text-sm">
      <svg className="animate-spin h-4 w-4 text-blue-500" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path  className="opacity-75"  fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
      </svg>
      Loading dashboard…
    </div>
  );

  // ── Error ──────────────────────────────────────────────────────────────────
  if (error || !plan || !heatmap) return (
    <div className="min-h-screen bg-[#060d1f] p-8">
      <p className="text-red-400 text-sm">
        Failed to load dashboard.{" "}
        <a href="/login" className="underline text-blue-400 hover:text-blue-300">Sign in again</a>
      </p>
    </div>
  );

  const currentYear  = new Date().getFullYear();
  const weeks        = buildWeekColumns(heatmap.activity ?? {}, currentYear);
  const monthLabels  = monthLabelsRow(weeks);
  const totalDays    = Object.values(heatmap.activity ?? {}).filter(v => v > 0).length;
  const streak       = heatmap.current_streak ?? 0;
  const gridWidthPx  = weeks.length * COL_STEP - GAP;

  const firstName = profile?.name?.split(" ")[0] || "";
  const initials = profile?.name
    ? profile.name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()
    : "";

  const weakPreview = recommendations?.weak_topics?.slice(0, 3) ?? [];
  const strongPreview = recommendations?.strong_topics?.slice(0, 3) ?? [];

  const quickStats = [
    { label: "Avg accuracy", value: `${plan.average_accuracy.toFixed(1)}%`, color: "text-blue-400" },
    { label: "Active days",  value: totalDays,                              color: "text-emerald-400" },
    { label: "Day streak",   value: streak,                                 color: "text-orange-400" },
  ];

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#060d1f] p-8 space-y-8">

      {/* Ambient glows */}
      <div className="pointer-events-none fixed -top-40 -left-40 w-[500px] h-[500px] rounded-full bg-blue-600/10 blur-[120px]" />
      <div className="pointer-events-none fixed bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-indigo-700/10 blur-[90px]" />

      {/* ── GREETING / IDENTITY ──────────────────────────────────────────── */}
      <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 flex items-center gap-5 shadow-xl shadow-black/20">
        {initials && (
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xl font-bold shadow-lg shadow-blue-500/30 shrink-0">
            {initials}
          </div>
        )}
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white">
            {getGreeting()}{firstName ? `, ${firstName}` : ""}
          </h1>
          {profile?.email && (
            <p className="text-sm text-slate-400 mt-0.5">{profile.email}</p>
          )}
        </div>

        {/* Quick stat strip */}
        <div className="hidden md:flex items-center gap-6">
          {quickStats.map((s) => (
            <div key={s.label} className="text-right">
              <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-[11px] text-slate-500 whitespace-nowrap">{s.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── STUDY PLAN ────────────────────────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xl">🧠</span>
          <h2 className="text-lg font-semibold text-white">Study Plan</h2>
          <span className="ml-auto text-xs text-slate-500 font-mono">
            avg accuracy
            <span className="ml-1.5 text-white font-semibold">
              {plan.average_accuracy.toFixed(1)}%
            </span>
          </span>
        </div>

        <div className="bg-white/[0.04] backdrop-blur border border-white/[0.08] rounded-2xl p-7 shadow-xl shadow-black/20">
          {/* Accuracy bar */}
          <div className="mb-6">
            <div className="flex justify-between text-sm text-slate-500 mb-2">
              <span>Current accuracy</span>
              <span className="text-white">{plan.average_accuracy.toFixed(1)}%</span>
            </div>
            <div className="h-2 w-full rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-600 to-blue-400 transition-all duration-700"
                style={{ width: `${Math.min(plan.average_accuracy, 100)}%` }}
              />
            </div>
          </div>

          {/* Plan items */}
          <ul className="space-y-3.5">
            {plan.plan.map((step, i) => (
              <li key={i} className="flex items-start gap-3.5">
                <span className="mt-0.5 w-6 h-6 rounded-full bg-blue-500/15 border border-blue-500/25
                                 flex items-center justify-center text-blue-400 text-xs font-semibold shrink-0">
                  {i + 1}
                </span>
                <span className="text-slate-300 text-[15px] leading-relaxed">{step}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ── HEATMAP ───────────────────────────────────────────────────────── */}

      <section>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xl">🤖</span>
          <h2 className="text-lg font-semibold text-white">AI Recommendations</h2>
          <span className="ml-auto text-xs text-slate-500 font-mono">
            learning score
            <span className="ml-1.5 text-white font-semibold">
              {recommendations?.learning_score ?? 0}/100
            </span>
          </span>
        </div>

        <div className="grid md:grid-cols-3 gap-4 mb-4">
          <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 shadow-xl shadow-black/20">
            <p className="text-xs text-slate-500 font-medium uppercase tracking-widest mb-2">Learning Score</p>
            <p className="text-3xl font-bold text-blue-400">{recommendations?.learning_score ?? 0}</p>
            <div className="mt-3 h-2 w-full rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-600 to-indigo-400"
                style={{ width: `${Math.min(recommendations?.learning_score ?? 0, 100)}%` }}
              />
            </div>
          </div>

          <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 shadow-xl shadow-black/20">
            <p className="text-xs text-slate-500 font-medium uppercase tracking-widest mb-3">Top Weak Topics</p>
            {weakPreview.length > 0 ? (
              <div className="space-y-2">
                {weakPreview.map((topic) => (
                  <div key={topic.topic} className="flex items-center justify-between gap-3 text-sm">
                    <span className="text-slate-300 capitalize truncate">{topic.topic}</span>
                    <span className="text-red-300 font-semibold shrink-0">{topic.accuracy.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-600">No weak topics found yet.</p>
            )}
          </div>

          <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 shadow-xl shadow-black/20">
            <p className="text-xs text-slate-500 font-medium uppercase tracking-widest mb-3">Top Strong Topics</p>
            {strongPreview.length > 0 ? (
              <div className="space-y-2">
                {strongPreview.map((topic) => (
                  <div key={topic.topic} className="flex items-center justify-between gap-3 text-sm">
                    <span className="text-slate-300 capitalize truncate">{topic.topic}</span>
                    <span className="text-emerald-300 font-semibold shrink-0">{topic.accuracy.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-600">Strong topics appear after consistent high accuracy.</p>
            )}
          </div>
        </div>

        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {(recommendations?.recommendations ?? []).length > 0 ? (
            recommendations!.recommendations.map((item) => (
              <div key={`${item.type}-${item.title}`} className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 shadow-xl shadow-black/20">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <h3 className="text-white font-semibold leading-snug">{item.title}</h3>
                  <span className={`text-[10px] uppercase tracking-widest px-2 py-1 rounded-full border ${priorityBadgeClass(item.priority)}`}>
                    {item.priority}
                  </span>
                </div>
                <p className="text-sm text-slate-400 leading-6">{item.description}</p>
              </div>
            ))
          ) : (
            <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 shadow-xl shadow-black/20 md:col-span-2 xl:col-span-3">
              <p className="text-sm text-slate-500">Complete quizzes and generate notes to unlock personalized recommendations.</p>
            </div>
          )}
        </div>
      </section>
      <section>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xl">🔥</span>
          <h2 className="text-lg font-semibold text-white">Activity Heatmap</h2>
          <span className="text-xs text-slate-500 font-mono">{currentYear}</span>

          {/* Streak + active days pill */}
          <div className="ml-auto flex items-center gap-4">
            {streak > 0 && (
              <span className="flex items-center gap-1 text-sm text-orange-400 font-medium">
                🔥 {streak}-day streak
              </span>
            )}
            <span className="text-sm text-slate-500">
              <span className="text-white font-medium">{totalDays}</span> active days
            </span>
          </div>
        </div>

        <div className="bg-white/[0.04] backdrop-blur border border-white/[0.08] rounded-2xl p-7 shadow-xl shadow-black/20">
          <div className="overflow-x-auto pb-1 -mx-1 px-1">
            <div className="inline-block min-w-full">

              <div className="flex">
                {/* Y-axis spacer to align under the day labels column */}
                <div className="w-9 shrink-0" />

                {/* Month labels row */}
                <div className="relative h-5 mb-1.5" style={{ width: `${gridWidthPx}px` }}>
                  {monthLabels.map(({ label, col }) => (
                    <span
                      key={`${label}-${col}`}
                      className="absolute top-0 text-[11px] font-medium text-slate-500 tracking-wide whitespace-nowrap"
                      style={{ left: `${col * COL_STEP}px` }}
                    >
                      {label}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex">
                {/* Day-of-week labels */}
                <div
                  className="flex flex-col w-9 shrink-0 text-[11px] text-slate-500 font-medium"
                  style={{ gap: `${GAP}px` }}
                >
                  <div style={{ height: `${CELL}px`, lineHeight: `${CELL}px` }}>Mon</div>
                  <div style={{ height: `${CELL}px`, lineHeight: `${CELL}px` }}>Tue</div>
                  <div style={{ height: `${CELL}px`, lineHeight: `${CELL}px` }}>Wed</div>
                  <div style={{ height: `${CELL}px`, lineHeight: `${CELL}px` }}>Thu</div>
                  <div style={{ height: `${CELL}px`, lineHeight: `${CELL}px` }}>Fri</div>
                  <div style={{ height: `${CELL}px`, lineHeight: `${CELL}px` }}>Sat</div>
                  <div style={{ height: `${CELL}px`, lineHeight: `${CELL}px` }}>Sun</div>
                </div>

                {/* Grid */}
                <div className="flex" style={{ gap: `${GAP}px` }}>
                  {weeks.map((col, wi) => (
                    <div key={wi} className="flex flex-col" style={{ gap: `${GAP}px` }}>
                      {col.map((cell, di) => {
                        if (!cell) {
                          // Padding slot from the partial week before Jan 1
                          // or after Dec 31 — rendered as inert empty space.
                          return (
                            <div
                              key={`pad-${wi}-${di}`}
                              style={{ width: `${CELL}px`, height: `${CELL}px` }}
                            />
                          );
                        }
                        const { date, count } = cell;
                        return (
                          <button
                            key={date}
                            type="button"
                            aria-label={`${formatLongDate(date)}: ${count} ${count === 1 ? "activity" : "activities"}`}
                            onMouseEnter={() => setHoveredCell({ date, count })}
                            onMouseLeave={() => setHoveredCell(null)}
                            onFocus={() => setHoveredCell({ date, count })}
                            onBlur={() => setHoveredCell(null)}
                            style={{ width: `${CELL}px`, height: `${CELL}px` }}
                            className={`rounded-[3px] cursor-default transition-transform duration-100
                                        hover:scale-[1.35] hover:z-10 focus:outline-none focus-visible:ring-1
                                        focus-visible:ring-blue-400 focus-visible:scale-[1.35] focus-visible:z-10
                                        ${getCellIntensity(count)}`}
                          />
                        );
                      })}
                    </div>
                  ))}
                </div>
              </div>

            </div>
          </div>

          {/* Footer row: live tooltip on the left, legend on the right */}
          <div className="flex items-center justify-between mt-5 pt-4 border-t border-white/[0.06]">
            <span className="text-xs text-slate-500 tabular-nums">
              {hoveredCell
                ? <>
                    <span className="text-slate-300 font-medium">
                      {hoveredCell.count} {hoveredCell.count === 1 ? "activity" : "activities"}
                    </span>
                    {" "}on {formatLongDate(hoveredCell.date)}
                  </>
                : "Hover a cell to see details"}
            </span>

            <div className="flex items-center gap-2 text-[11px] text-slate-600">
              <span>Less</span>
              {[0, 1, 3, 5, 7].map(v => (
                <div
                  key={v}
                  style={{ width: `${CELL}px`, height: `${CELL}px` }}
                  className={`rounded-[3px] ${getCellIntensity(v)}`}
                />
              ))}
              <span>More</span>
            </div>
          </div>
        </div>
      </section>

    </div>
  );
}