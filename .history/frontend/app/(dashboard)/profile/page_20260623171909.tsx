// LOCATION: app/(dashboard)/profile/page.tsx
"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import {
  getAnalyticsSummary,
  getMasterySummary,
  getRecommendations,
  getProfileInfo,
  getStrongTopics,
  getTopicMastery,
  getWeakTopics,
  type MasterySummary,
  type RecommendationsResponse,
  type PersistedMasteryLevel,
  type StudentTopicMastery,
} from "@/lib/api";

interface Profile {
  student_id: number | null;
  name: string;
  email: string;
  joined?: string;
  topics_studied: string[];
  total_questions_asked: number;
  total_study_sessions: number;
  total_documents_uploaded: number;
  current_streak: number;
}

interface AnalyticsSummary {
  total_quizzes: number;
  average_accuracy: number;
  total_notes_generated: number;
  total_quizzes_generated: number;
  documents_uploaded: number;
  recent_activity: {
    type: string;
    label: string;
    topic: string | null;
    accuracy: number | null;
    timestamp: string;
  }[];
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
      Loading profile...
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return <p className="text-slate-600 text-sm">{message}</p>;
}

function accuracyColor(accuracy: number) {
  if (accuracy >= 75) return "text-emerald-400";
  if (accuracy >= 60) return "text-blue-400";
  if (accuracy >= 40) return "text-orange-400";
  return "text-red-400";
}

function formatDate(value: string | null | undefined) {
  if (!value) return "No practice yet";
  return new Date(value).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
}

function getPerformanceSummary(summary: MasterySummary) {
  if (summary.total_topics === 0) return "No topic mastery has been recorded yet. Complete a quiz to establish your baseline.";
  if (summary.mastered_topics === summary.total_topics) return "Every tracked topic is currently mastered. Maintain this with periodic review.";
  if (summary.mastered_topics + summary.strong_topics >= Math.ceil(summary.total_topics * 0.7)) return "Most tracked topics are strong or mastered. Focused review can close the remaining gaps.";
  if (summary.weak_topics + summary.needs_work_topics > summary.strong_topics + summary.mastered_topics) return "More topics need focused practice than are currently strong. Start with the weakest topics below.";
  return "Your topic profile is balanced, with clear opportunities to move improving topics into the strong range.";
}

function TopicRow({ topic }: { topic: StudentTopicMastery }) {
  const style = levelStyles[topic.mastery_level] ?? levelStyles["Needs Work"];
  return (
    <div>
      <div className="flex items-start justify-between gap-4 text-sm mb-1.5">
        <div>
          <p className="text-slate-300 font-medium capitalize">{topic.topic}</p>
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
}

export default function ProfilePage() {
  useAuth();

  const [profile, setProfile] = useState<Profile | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [summary, setSummary] = useState<MasterySummary>(emptySummary);
  const [mastery, setMastery] = useState<StudentTopicMastery[]>([]);
  const [strongTopics, setStrongTopics] = useState<StudentTopicMastery[]>([]);
  const [weakTopics, setWeakTopics] = useState<StudentTopicMastery[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionError, setSessionError] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setSessionError(false);

    const [infoRes, analyticsRes, summaryRes, masteryRes, strongRes, weakRes, recommendationsRes] = await Promise.allSettled([
      getProfileInfo(),
      getAnalyticsSummary(),
      getMasterySummary(),
      getTopicMastery(),
      getStrongTopics(),
      getWeakTopics(),
      getRecommendations(),
    ]);

    const profileInfo = infoRes.status === "fulfilled" ? infoRes.value : null;

    if (!profileInfo || profileInfo.detail) {
      setSessionError(true);
      setLoading(false);
      return;
    }

    setProfile({
      student_id: profileInfo.student_id ?? null,
      name: profileInfo.name,
      email: profileInfo.email,
      joined: profileInfo.joined,
      topics_studied: profileInfo.topics_studied ?? profileInfo.notes_topics ?? [],
      total_questions_asked: profileInfo.total_questions_asked ?? 0,
      total_study_sessions: profileInfo.total_study_sessions ?? 0,
      total_documents_uploaded: profileInfo.total_documents_uploaded ?? 0,
      current_streak: profileInfo.current_streak ?? 0,
    });

    setAnalytics(analyticsRes.status === "fulfilled" && !analyticsRes.value?.detail ? analyticsRes.value : null);
    setSummary(summaryRes.status === "fulfilled" ? summaryRes.value : emptySummary);
    setMastery(masteryRes.status === "fulfilled" ? masteryRes.value : []);
    setStrongTopics(strongRes.status === "fulfilled" ? strongRes.value : []);
    setWeakTopics(weakRes.status === "fulfilled" ? weakRes.value : []);
    setRecommendations(recommendationsRes.status === "fulfilled" ? recommendationsRes.value : null);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const totalWeak = summary.weak_topics + summary.needs_work_topics;
  const totalStrong = summary.mastered_topics + summary.strong_topics;
  const hasMastery = summary.total_topics > 0;
  const initials = profile?.name.split(" ").map((word) => word[0]).slice(0, 2).join("").toUpperCase() || "ST";

  const topMastery = useMemo(
    () => [...mastery].sort((a, b) => b.accuracy - a.accuracy || b.attempts - a.attempts),
    [mastery]
  );

  const strongestTopic = recommendations?.strong_topics?.[0]?.topic ?? strongTopics[0]?.topic ?? "Not available";
  const weakestTopic = recommendations?.weak_topics?.[0]?.topic ?? weakTopics[0]?.topic ?? "Not available";

  const masteryStats = [
    {
      label: "Learning Score",
      value: recommendations?.learning_score ?? 0,
      valueColor: "text-blue-400",
      iconColor: "text-blue-400 bg-blue-500/10 border border-blue-500/20",
    },
    {
      label: "Strongest Topic",
      value: strongestTopic,
      valueColor: "text-emerald-400",
      iconColor: "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20",
    },
    {
      label: "Weakest Topic",
      value: weakestTopic,
      valueColor: "text-orange-400",
      iconColor: "text-orange-400 bg-orange-500/10 border border-orange-500/20",
    },
    {
      label: "Total Mastered Topics",
      value: summary.mastered_topics,
      valueColor: "text-yellow-300",
      iconColor: "text-yellow-300 bg-yellow-400/10 border border-yellow-400/20",
    },
  ];

  const engagementStats = profile ? [
    { label: "Questions Asked", value: profile.total_questions_asked, valueColor: "text-cyan-400" },
    { label: "Study Sessions", value: profile.total_study_sessions, valueColor: "text-teal-400" },
    { label: "Documents Uploaded", value: profile.total_documents_uploaded, valueColor: "text-sky-400" },
    { label: "Current Streak", value: `${profile.current_streak} ${profile.current_streak === 1 ? "day" : "days"}`, valueColor: "text-amber-400" },
  ] : [];

  if (loading) return <LoadingState />;

  if (sessionError || !profile) {
    return (
      <div className="min-h-screen bg-[#060d1f] p-8">
        <p className="text-red-400">
          Session not found. Please <a href="/login" className="underline text-blue-400 hover:text-blue-300">sign in</a>.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#060d1f] p-8 space-y-8">
      <div className="pointer-events-none fixed -top-40 -left-40 w-[500px] h-[500px] rounded-full bg-blue-600/10 blur-[120px]" />
      <div className="pointer-events-none fixed bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-indigo-700/10 blur-[90px]" />

      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-white">Student Profile</h1>
      </div>

      <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 flex items-center gap-5 shadow-xl shadow-black/20">
        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xl font-bold shadow-lg shadow-blue-500/30 shrink-0">
          {initials}
        </div>
        <div className="flex-1">
          <p className="text-xl font-bold text-white">{profile.name}</p>
          <p className="text-sm text-slate-400">{profile.email}</p>
          {profile.joined && (
            <p className="text-xs text-slate-500 mt-0.5">
              Joined {new Date(profile.joined).toLocaleDateString("en-IN", { year: "numeric", month: "long", day: "numeric" })}
            </p>
          )}
        </div>
        <div className="hidden sm:flex flex-col items-end gap-1">
          <p className="text-xs text-slate-500 uppercase tracking-widest">Topic Accuracy</p>
          <p className={`text-3xl font-bold ${accuracyColor(summary.average_accuracy)}`}>{summary.average_accuracy.toFixed(1)}%</p>
        </div>
      </div>

      <div className="grid md:grid-cols-4 gap-4">
        {masteryStats.map((stat) => (
          <div key={stat.label} className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 flex flex-col gap-3 shadow-xl shadow-black/20">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${stat.iconColor}`}>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className={`text-2xl font-bold ${stat.valueColor} break-words`}>{stat.value}</p>
            <p className="text-xs text-slate-500">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-4 gap-4">
        {engagementStats.map((stat) => (
          <div key={stat.label} className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 shadow-xl shadow-black/20">
            <p className={`text-2xl font-bold ${stat.valueColor} break-words`}>{stat.value}</p>
            <p className="text-xs text-slate-500 mt-2">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-5 gap-4">
        <div className="lg:col-span-2 bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">Overall Performance</p>
          <p className={`text-4xl font-bold ${accuracyColor(summary.average_accuracy)} mb-3`}>{summary.average_accuracy.toFixed(1)}%</p>
          <p className="text-sm text-slate-400 leading-6">{getPerformanceSummary(summary)}</p>
          <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
              <p className="text-slate-500 text-xs mb-1">Correct Answers</p>
              <p className="text-white font-semibold">{summary.total_correct_answers}</p>
            </div>
            <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
              <p className="text-slate-500 text-xs mb-1">Question Attempts</p>
              <p className="text-white font-semibold">{summary.total_attempts}</p>
            </div>
            <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
              <p className="text-slate-500 text-xs mb-1">Quiz Results</p>
              <p className="text-white font-semibold">{analytics?.total_quizzes ?? 0}</p>
            </div>
            <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
              <p className="text-slate-500 text-xs mb-1">Last Practice</p>
              <p className="text-white font-semibold">{formatDate(summary.last_practiced)}</p>
            </div>
          </div>
        </div>

        <div className="lg:col-span-3 bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
          <h2 className="text-lg font-bold text-white mb-5">Mastery Level Distribution</h2>
          {hasMastery ? (
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
          ) : (
            <EmptyState message="No distribution yet. Finish a quiz to start tracking topic mastery." />
          )}
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
          <h2 className="text-lg font-bold text-white mb-5">Topic Strengths</h2>
          {strongTopics.length > 0 ? (
            <div className="space-y-4">
              {strongTopics.slice(0, 5).map((topic) => <TopicRow key={topic.id} topic={topic} />)}
            </div>
          ) : (
            <EmptyState message="No strong topics yet. Reach 75% accuracy in a topic to see it here." />
          )}
        </div>

        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
          <h2 className="text-lg font-bold text-white mb-5">Topic Weaknesses</h2>
          {weakTopics.length > 0 ? (
            <div className="space-y-4">
              {weakTopics.slice(0, 5).map((topic) => <TopicRow key={topic.id} topic={topic} />)}
            </div>
          ) : (
            <EmptyState message="No weak topics currently tracked." />
          )}
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
          <h2 className="text-lg font-bold text-white mb-5">All Topic Mastery</h2>
          {topMastery.length > 0 ? (
            <div className="space-y-4">
              {topMastery.map((topic) => <TopicRow key={topic.id} topic={topic} />)}
            </div>
          ) : (
            <EmptyState message="No topics have quiz results yet." />
          )}
        </div>

        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
          <h2 className="text-lg font-bold text-white mb-5">Recent Activity</h2>
          {analytics?.recent_activity && analytics.recent_activity.length > 0 ? (
            <div className="space-y-2.5">
              {analytics.recent_activity.slice(0, 5).map((item, index) => (
                <div key={`${item.timestamp}-${index}`} className="flex items-center justify-between gap-4 text-sm">
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
            <EmptyState message="No recent activity yet." />
          )}
        </div>
      </div>
    </div>
  );
}
