// LOCATION: app/(dashboard)/analytics/page.tsx
"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import {
  getAnalyticsSummary,
  getMasterySummary,
  getRecommendations,
  getRecommendationSummary,
  getStrongTopics,
  getTopicMastery,
  getWeakTopics,
  type MasterySummary,
  type RecommendationsResponse,
  type RecommendationSummary,
  type PersistedMasteryLevel,
  type StudentTopicMastery,
} from "@/lib/api";

interface RecentActivityItem {
  type: string;
  label: string;
  topic: string | null;
  accuracy: number | null;
  timestamp: string;
}

interface WeeklyActivityItem {
  week_start: string;
  count: number;
}

interface AnalyticsSummary {
  total_quizzes: number;
  average_accuracy: number;
  total_notes_generated: number;
  total_quizzes_generated: number;
  recent_activity: RecentActivityItem[];
  quiz_questions_answered: number;
  documents_uploaded: number;
  estimated_study_minutes: number;
  weekly_activity: WeeklyActivityItem[];
}

const masteryLevels: PersistedMasteryLevel[] = ["Mastered", "Strong", "Improving", "Weak", "Needs Work"];

const levelStyles: Record<PersistedMasteryLevel, { text: string; bg: string; border: string; bar: string }> = {
  Mastered: { text: "text-yellow-300", bg: "bg-yellow-400/10", border: "border-yellow-400/25", bar: "bg-yellow-300" },
  Strong: { text: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/25", bar: "bg-emerald-400" },
  Improving: { text: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/25", bar: "bg-blue-400" },
  Weak: { text: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/25", bar: "bg-orange-400" },
  "Needs Work": { text: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/25", bar: "bg-red-400" },
};

const emptySummary: MasterySummary = {
  total_topics: 0,
  total_attempts: 0,
  total_correct_answers: 0,
  average_accuracy: 0,
  mastered_topics: 0,
  strong_topics: 0,
  improving_topics: 0,
  weak_topics: 0,
  needs_work_topics: 0,
  mastery_distribution: {
    Mastered: 0,
    Strong: 0,
    Improving: 0,
    Weak: 0,
    "Needs Work": 0,
  },
  last_practiced: null,
};

function LoadingState() {
  return (
    <div className="min-h-screen bg-[#060d1f] p-8 flex items-center gap-3 text-slate-400">
      <svg className="animate-spin h-5 w-5 text-blue-500" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
      </svg>
      Loading analytics...
    </div>
  );
}

function EmptyPanel({ title, message }: { title: string; message: string }) {
  return (
    <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
      <h2 className="text-lg font-bold text-white mb-2">{title}</h2>
      <p className="text-sm text-slate-500">{message}</p>
    </div>
  );
}

function formatDate(value: string | null) {
  if (!value) return "Not practiced yet";
  return new Date(value).toLocaleDateString("en-IN", { month: "short", day: "numeric", year: "numeric" });
}

function accuracyColor(accuracy: number) {
  if (accuracy >= 75) return "text-emerald-400";
  if (accuracy >= 60) return "text-blue-400";
  if (accuracy >= 40) return "text-orange-400";
  return "text-red-400";
}

function getInsight(summary: MasterySummary) {
  if (summary.total_topics === 0) return "Take your first topic quiz to unlock mastery insights.";
  if (summary.needs_work_topics > 0) return "Prioritize topics marked Needs Work before adding new material.";
  if (summary.weak_topics > 0) return "Your biggest gains are likely in Weak topics with recent practice.";
  if (summary.improving_topics > 0) return "Improving topics are close to becoming strengths with a few focused attempts.";
  if (summary.mastered_topics === summary.total_topics) return "All tracked topics are mastered. Keep them warm with periodic review.";
  return "Your topic mastery is trending toward strong coverage.";
}

export default function AnalyticsPage() {
  useAuth();

  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [summary, setSummary] = useState<MasterySummary>(emptySummary);
  const [mastery, setMastery] = useState<StudentTopicMastery[]>([]);
  const [weakTopics, setWeakTopics] = useState<StudentTopicMastery[]>([]);
  const [strongTopics, setStrongTopics] = useState<StudentTopicMastery[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationsResponse | null>(null);
  const [recommendationSummary, setRecommendationSummary] = useState<RecommendationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [analyticsRes, summaryRes, masteryRes, weakRes, strongRes, recommendationsRes, recommendationSummaryRes] = await Promise.allSettled([
        getAnalyticsSummary(),
        getMasterySummary(),
        getTopicMastery(),
        getWeakTopics(),
        getStrongTopics(),
        getRecommendations(),
        getRecommendationSummary(),
      ]);

      if (analyticsRes.status === "fulfilled" && !analyticsRes.value?.detail) {
        setAnalytics(analyticsRes.value);
      } else {
        setAnalytics(null);
      }

      setSummary(summaryRes.status === "fulfilled" ? summaryRes.value : emptySummary);
      setMastery(masteryRes.status === "fulfilled" ? masteryRes.value : []);
      setWeakTopics(weakRes.status === "fulfilled" ? weakRes.value : []);
      setStrongTopics(strongRes.status === "fulfilled" ? strongRes.value : []);
      setRecommendations(recommendationsRes.status === "fulfilled" ? recommendationsRes.value : null);
      setRecommendationSummary(recommendationSummaryRes.status === "fulfilled" ? recommendationSummaryRes.value : null);

      if (analyticsRes.status === "rejected" && summaryRes.status === "rejected") {
        setError("Unable to load analytics right now. Please try again after signing in again.");
      }
    } catch (err) {
      console.error(err);
      setError("Unable to load analytics right now. Please try again after signing in again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  const maxWeekly = Math.max(1, ...(analytics?.weekly_activity ?? []).map((w) => w.count));
  const hasMastery = summary.total_topics > 0;
  const totalWeak = summary.weak_topics + summary.needs_work_topics;
  const totalStrong = summary.mastered_topics + summary.strong_topics;

  const topTopics = useMemo(
    () => [...mastery].sort((a, b) => b.attempts - a.attempts || b.accuracy - a.accuracy),
    [mastery]
  );

  const learningScore = recommendations?.learning_score ?? 0;
  const recommendationCount = recommendationSummary?.recommendation_count ?? recommendations?.recommendations.length ?? 0;

  const statCards = [
    { label: "Learning Score", value: learningScore, color: "text-blue-400" },
    { label: "Tracked Topics", value: summary.total_topics, color: "text-indigo-400" },
    { label: "Topic Accuracy", value: `${summary.average_accuracy.toFixed(1)}%`, color: accuracyColor(summary.average_accuracy) },
    { label: "Questions Answered", value: summary.total_attempts, color: "text-cyan-400" },
  ];

  if (loading) return <LoadingState />;

  if (error) {
    return (
      <div className="min-h-screen bg-[#060d1f] p-8">
        <p className="text-red-400">
          {error} <a href="/login" className="underline text-blue-400 hover:text-blue-300">Sign in</a>
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#060d1f] p-8 space-y-8">
      <div className="pointer-events-none fixed -top-40 -left-40 w-[500px] h-[500px] rounded-full bg-blue-600/10 blur-[120px]" />
      <div className="pointer-events-none fixed bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-indigo-700/10 blur-[90px]" />

      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-white">Analytics Dashboard</h1>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map(({ label, value, color }) => (
          <div key={label} className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 shadow-xl shadow-black/20">
            <p className="text-xs text-slate-500 font-medium uppercase tracking-widest mb-2">{label}</p>
            <p className={`text-3xl font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {!hasMastery ? (
        <EmptyPanel
          title="No Mastery Data Yet"
          message="Complete a quiz result to start building topic-level mastery, strengths, weaknesses, and performance insights."
        />
      ) : (
        <>
          <div className="grid lg:grid-cols-5 gap-4">
            <div className="lg:col-span-3 bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-lg font-bold text-white">Mastery Distribution</h2>
                <span className="text-xs text-slate-500">Last practiced {formatDate(summary.last_practiced)}</span>
              </div>
              <div className="space-y-4">
                {masteryLevels.map((level) => {
                  const count = summary.mastery_distribution?.[level] ?? 0;
                  const percent = summary.total_topics ? (count / summary.total_topics) * 100 : 0;
                  const style = levelStyles[level];
                  return (
                    <div key={level}>
                      <div className="flex justify-between text-sm mb-1.5">
                        <span className={`${style.text} font-medium`}>{level}</span>
                        <span className="text-slate-500">{count} topic{count === 1 ? "" : "s"}</span>
                      </div>
                      <div className="w-full bg-white/5 rounded-full h-2 overflow-hidden">
                        <div className={`h-2 rounded-full ${style.bar}`} style={{ width: `${percent}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="lg:col-span-2 bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
              <h2 className="text-lg font-bold text-white mb-5">Performance Insights</h2>
              <div className="grid grid-cols-2 gap-3 mb-5">
                <div className="rounded-2xl border border-blue-500/20 bg-blue-500/10 p-4">
                  <p className="text-xs uppercase tracking-widest text-blue-300/80 mb-2">Learning Score</p>
                  <p className="text-3xl font-bold text-blue-400">{learningScore}</p>
                </div>
                <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-4">
                  <p className="text-xs uppercase tracking-widest text-red-300/80 mb-2">Weak Topics</p>
                  <p className="text-3xl font-bold text-red-300">{recommendationSummary?.weak_count ?? totalWeak}</p>
                </div>
                <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4">
                  <p className="text-xs uppercase tracking-widest text-emerald-300/80 mb-2">Strong Topics</p>
                  <p className="text-3xl font-bold text-emerald-400">{recommendationSummary?.strong_count ?? totalStrong}</p>
                </div>
                <div className="rounded-2xl border border-yellow-500/20 bg-yellow-500/10 p-4">
                  <p className="text-xs uppercase tracking-widest text-yellow-300/80 mb-2">Recommendations</p>
                  <p className="text-3xl font-bold text-yellow-300">{recommendationCount}</p>
                </div>
              </div>
              <p className="text-sm text-slate-400 leading-6">{getInsight(summary)}</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
              <h2 className="text-lg font-bold text-white mb-5">Topic Performance Metrics</h2>
              {topTopics.length > 0 ? (
                <div className="space-y-3">
                  {topTopics.map((topic) => {
                    const style = levelStyles[topic.mastery_level] ?? levelStyles["Needs Work"];
                    return (
                      <div key={topic.id}>
                        <div className="flex items-start justify-between gap-4 text-sm mb-1">
                          <div>
                            <p className="text-slate-300 capitalize font-medium">{topic.topic}</p>
                            <p className="text-xs text-slate-600">{topic.correct_answers}/{topic.attempts} correct</p>
                          </div>
                          <div className="text-right">
                            <p className={`font-semibold ${accuracyColor(topic.accuracy)}`}>{topic.accuracy.toFixed(1)}%</p>
                            <span className={`inline-flex mt-1 px-2 py-0.5 rounded-full text-[10px] border ${style.bg} ${style.border} ${style.text}`}>
                              {topic.mastery_level}
                            </span>
                          </div>
                        </div>
                        <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
                          <div className="h-1.5 rounded-full bg-gradient-to-r from-blue-600 to-indigo-400" style={{ width: `${Math.min(topic.accuracy, 100)}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-slate-600 text-sm">Take a quiz to see topic performance.</p>
              )}
            </div>

            <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
              <h2 className="text-lg font-bold text-white mb-5">Topic Accuracy Insights</h2>
              <div className="space-y-5">
                <div>
                  <p className="text-xs uppercase tracking-widest text-slate-500 mb-3">Strengths</p>
                  {strongTopics.length > 0 ? (
                    <div className="space-y-2">
                      {strongTopics.slice(0, 5).map((topic) => (
                        <div key={topic.id} className="flex justify-between text-sm">
                          <span className="text-slate-300 capitalize">{topic.topic}</span>
                          <span className="text-emerald-400 font-semibold">{topic.accuracy.toFixed(1)}%</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-600">No strong topics yet.</p>
                  )}
                </div>

                <div>
                  <p className="text-xs uppercase tracking-widest text-slate-500 mb-3">Needs Focus</p>
                  {weakTopics.length > 0 ? (
                    <div className="space-y-2">
                      {weakTopics.slice(0, 5).map((topic) => (
                        <div key={topic.id} className="flex justify-between text-sm">
                          <span className="text-slate-300 capitalize">{topic.topic}</span>
                          <span className="text-orange-400 font-semibold">{topic.accuracy.toFixed(1)}%</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-600">No weak topics currently tracked.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
          <h2 className="text-lg font-bold text-white mb-5">Learning Trends</h2>
          {analytics?.weekly_activity && analytics.weekly_activity.length > 0 ? (
            <div className="flex items-end gap-2 h-32">
              {analytics.weekly_activity.map((week) => (
                <div key={week.week_start} className="flex-1 flex flex-col items-center gap-1.5">
                  <div
                    className="w-full rounded-t-md bg-gradient-to-t from-blue-600 to-indigo-400 transition-all duration-500"
                    style={{ height: `${Math.max(4, (week.count / maxWeekly) * 100)}%` }}
                    title={`${week.count} activities`}
                  />
                  <span className="text-[10px] text-slate-600">
                    {new Date(week.week_start).toLocaleDateString("en-IN", { month: "short", day: "numeric" })}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-600 text-sm">No weekly activity yet.</p>
          )}
        </div>

        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
          <h2 className="text-lg font-bold text-white mb-5">Recent Activity</h2>
          {analytics?.recent_activity && analytics.recent_activity.length > 0 ? (
            <div className="space-y-2.5">
              {analytics.recent_activity.slice(0, 5).map((item, index) => (
                <div key={`${item.timestamp}-${index}`} className="flex items-center justify-between text-sm gap-4">
                  <div>
                    <p className="text-slate-300 capitalize">{item.label}</p>
                    <p className="text-xs text-slate-600">{new Date(item.timestamp).toLocaleDateString("en-IN", { month: "short", day: "numeric" })}</p>
                  </div>
                  {item.accuracy !== null ? (
                    <span className="text-emerald-400 font-semibold">{item.accuracy}%</span>
                  ) : (
                    <span className="text-slate-600">No score</span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-600 text-sm">No recent activity yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
