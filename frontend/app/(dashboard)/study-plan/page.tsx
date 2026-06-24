"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { getFullStudyPlan, type FullStudyPlan } from "@/lib/api";

function percent(value: number) {
  return `${value.toFixed(1)}%`;
}

export default function StudyPlanPage() {
  useAuth();

  const [plan, setPlan] = useState<FullStudyPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPlan = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPlan(await getFullStudyPlan());
    } catch (err) {
      console.error("Study plan load failed:", err);
      setError("Unable to load your study plan. Please sign in again or try later.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPlan();
  }, [loadPlan]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#060d1f] p-8 flex items-center gap-3 text-slate-400 text-sm">
        <span className="h-4 w-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
        Loading study plan...
      </div>
    );
  }

  if (error || !plan) {
    return <div className="min-h-screen bg-[#060d1f] p-8 text-red-400 text-sm">{error ?? "Study plan unavailable."}</div>;
  }

  return (
    <div className="min-h-screen bg-[#060d1f] p-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white">Study Plan</h1>
        <p className="text-sm text-slate-500 mt-1">Generated from your quiz results, topic mastery, uploaded documents, and activity history.</p>
      </div>

      <div className="grid md:grid-cols-4 gap-4">
        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-5">
          <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Overall Accuracy</p>
          <p className="text-3xl font-bold text-blue-400">{percent(plan.overall_accuracy)}</p>
        </div>
        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-5">
          <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Learning Tier</p>
          <p className="text-3xl font-bold text-indigo-300 capitalize">{plan.accuracy_tier}</p>
        </div>
        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-5">
          <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Streak</p>
          <p className="text-3xl font-bold text-amber-300">{plan.current_streak}</p>
        </div>
        <div className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-5">
          <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Documents</p>
          <p className="text-3xl font-bold text-emerald-300">{plan.documents_available}</p>
        </div>
      </div>

      <section className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-6">
        <h2 className="text-lg font-bold text-white mb-4">Today</h2>
        {plan.daily_plan.length > 0 ? (
          <div className="space-y-3">
            {plan.daily_plan.map((task) => (
              <div key={`${task.order}-${task.topic}-${task.task_type}`} className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-4 flex items-start gap-4">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-500/15 text-sm font-bold text-blue-300">{task.order}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <p className="font-semibold text-white">{task.description}</p>
                    <span className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] uppercase tracking-widest text-slate-400">{task.priority}</span>
                  </div>
                  <p className="text-sm text-slate-500">{task.topic} · {task.difficulty} · {task.estimated_minutes} min</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">Take a quiz to generate a personalized daily plan.</p>
        )}
      </section>

      <div className="grid lg:grid-cols-2 gap-4">
        <section className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-6">
          <h2 className="text-lg font-bold text-white mb-4">Weak Topics</h2>
          {plan.weak_topics.length > 0 ? (
            <div className="space-y-3">
              {plan.weak_topics.map((topic) => (
                <div key={topic.topic} className="flex items-center justify-between gap-4 text-sm">
                  <span className="text-slate-300 capitalize">{topic.topic}</span>
                  <span className="font-semibold text-orange-300">{percent(topic.quiz_accuracy)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No weak topics tracked yet.</p>
          )}
        </section>

        <section className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-6">
          <h2 className="text-lg font-bold text-white mb-4">Strong Topics</h2>
          {plan.strong_topics.length > 0 ? (
            <div className="space-y-3">
              {plan.strong_topics.map((topic) => (
                <div key={topic.topic} className="flex items-center justify-between gap-4 text-sm">
                  <span className="text-slate-300 capitalize">{topic.topic}</span>
                  <span className="font-semibold text-emerald-300">{percent(topic.quiz_accuracy)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Strong topics appear after high-scoring quiz attempts.</p>
          )}
        </section>
      </div>

      <section className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-6">
        <h2 className="text-lg font-bold text-white mb-4">Four Week Plan</h2>
        <div className="grid md:grid-cols-2 gap-4">
          {plan.weekly_plan.map((week) => (
            <div key={week.week_number} className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-4">
              <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Week {week.week_number}</p>
              <p className="font-semibold text-white">{week.focus_area}</p>
              <p className="text-sm text-slate-400 mt-2">{week.milestone}</p>
              <p className="text-xs text-slate-500 mt-3">Target {percent(week.target_accuracy)} · {week.tasks_per_day} tasks/day</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {week.topics.map((topic) => (
                  <span key={topic} className="rounded-full border border-blue-500/20 bg-blue-500/10 px-2 py-1 text-xs text-blue-200">{topic}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-6">
        <h2 className="text-lg font-bold text-white mb-4">Recommendations</h2>
        <div className="space-y-2">
          {plan.recommendations.map((item) => (
            <p key={item} className="text-sm leading-6 text-slate-300">{item}</p>
          ))}
        </div>
      </section>
    </div>
  );
}
