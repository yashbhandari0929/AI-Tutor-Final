"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import {
  evaluateInterviewAnswer,
  generateInterviewQuestions,
  getInterviewAnalytics,
  getInterviewHistory,
  getInterviewReport,
  uploadResumeForInterview,
  type InterviewAnalyticsResponse,
  type InterviewDifficulty,
  type InterviewEvaluationResponse,
  type InterviewQuestionItem,
  type InterviewSessionItem,
  type ResumeAnalysisResponse,
} from "@/lib/api";

export default function ResumeInterviewPage() {
  useAuth();

  const fileRef = useRef<HTMLInputElement>(null);
  const [analysis, setAnalysis] = useState<ResumeAnalysisResponse | null>(null);
  const [questions, setQuestions] = useState<InterviewQuestionItem[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<InterviewQuestionItem | null>(null);
  const [answer, setAnswer] = useState("");
  const [evaluation, setEvaluation] = useState<InterviewEvaluationResponse | null>(null);
  const [history, setHistory] = useState<InterviewSessionItem[]>([]);
  const [report, setReport] = useState<(InterviewSessionItem & { readiness_score: number; weak_skill_areas: string[]; recommended_topics: string[] }) | null>(null);
  const [analytics, setAnalytics] = useState<InterviewAnalyticsResponse | null>(null);
  const [difficulty, setDifficulty] = useState<InterviewDifficulty>("Medium");
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeSessionId = analysis?.session_id ?? report?.id ?? null;

  const refreshInterviewData = useCallback(async (sessionId?: number) => {
    const [historyRes, analyticsRes, reportRes] = await Promise.allSettled([
      getInterviewHistory(),
      getInterviewAnalytics(),
      getInterviewReport(sessionId),
    ]);
    if (historyRes.status === "fulfilled") setHistory(historyRes.value.sessions ?? []);
    if (analyticsRes.status === "fulfilled") setAnalytics(analyticsRes.value);
    if (reportRes.status === "fulfilled") {
      setReport(reportRes.value);
      if (reportRes.value.questions?.length) setQuestions(reportRes.value.questions);
    }
  }, []);

  useEffect(() => {
    refreshInterviewData().catch((err) => console.error("Interview data load failed:", err));
  }, [refreshInterviewData]);

  const uploadResume = async (file: File) => {
    if (file.type !== "application/pdf") {
      setError("Only PDF resumes are supported.");
      return;
    }
    setLoading(true);
    setError(null);
    setEvaluation(null);
    try {
      const parsed = await uploadResumeForInterview(file);
      setAnalysis(parsed);
      setQuestions([]);
      setSelectedQuestion(null);
      await refreshInterviewData(parsed.session_id);
    } catch (err) {
      console.error("Resume upload failed:", err);
      setError(err instanceof Error ? err.message : "Resume upload failed.");
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const generateQuestions = async () => {
    if (!activeSessionId) {
      setError("Upload a resume before generating interview questions.");
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const response = await generateInterviewQuestions(activeSessionId, difficulty);
      setQuestions(response.questions ?? []);
      setSelectedQuestion(response.questions?.[0] ?? null);
      await refreshInterviewData(activeSessionId);
    } catch (err) {
      console.error("Question generation failed:", err);
      setError(err instanceof Error ? err.message : "Question generation failed.");
    } finally {
      setGenerating(false);
    }
  };

  const evaluateAnswer = async () => {
    if (!selectedQuestion || !answer.trim()) return;
    setEvaluating(true);
    setError(null);
    try {
      const response = await evaluateInterviewAnswer({
        session_id: activeSessionId ?? undefined,
        question_id: selectedQuestion.id,
        question: selectedQuestion.question,
        answer,
      });
      setEvaluation(response);
      setAnswer("");
      if (activeSessionId) await refreshInterviewData(activeSessionId);
    } catch (err) {
      console.error("Answer evaluation failed:", err);
      setError(err instanceof Error ? err.message : "Answer evaluation failed.");
    } finally {
      setEvaluating(false);
    }
  };

  const strengths = useMemo(() => analysis?.strengths ?? report?.recommended_topics ?? [], [analysis, report]);
  const weaknesses = useMemo(() => report?.weak_skill_areas ?? analysis?.skill_gap_analysis ?? [], [analysis, report]);

  return (
    <div className="min-h-screen bg-[#060d1f] p-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white">Resume Interview Prep</h1>
        <p className="text-sm text-slate-500 mt-1">Upload a resume, generate tailored questions, evaluate answers, and track readiness.</p>
      </div>

      {error && <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      <div className="grid lg:grid-cols-3 gap-4">
        <section className="lg:col-span-2 rounded-2xl border border-white/[0.08] bg-white/[0.04] p-6">
          <div className="flex items-center justify-between gap-4 mb-5">
            <div>
              <h2 className="text-lg font-bold text-white">Resume Analysis</h2>
              <p className="text-sm text-slate-500">PDF parsing and interview readiness are persisted to your profile.</p>
            </div>
            <input ref={fileRef} type="file" accept="application/pdf" className="hidden" onChange={(e) => e.target.files?.[0] && uploadResume(e.target.files[0])} />
            <button
              onClick={() => fileRef.current?.click()}
              disabled={loading}
              className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
            >
              {loading ? "Uploading..." : "Upload Resume"}
            </button>
          </div>

          {analysis ? (
            <div className="grid md:grid-cols-2 gap-4">
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-4">
                <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Resume</p>
                <p className="font-semibold text-white">{analysis.resume_name}</p>
                <p className="text-sm text-slate-500 mt-1">{analysis.name || "Candidate"}</p>
              </div>
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-4 grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Resume Score</p>
                  <p className="text-3xl font-bold text-blue-300">{analysis.resume_score}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">ATS Score</p>
                  <p className="text-3xl font-bold text-emerald-300">{analysis.ats_score}</p>
                </div>
              </div>
              <ListPanel title="Skills" items={analysis.skills} />
              <ListPanel title="Improvements" items={analysis.improvements} />
            </div>
          ) : report?.id ? (
            <p className="text-sm text-slate-400">Latest session loaded from history. Upload a new resume to start another prep session.</p>
          ) : (
            <p className="text-sm text-slate-500">No resume session yet.</p>
          )}
        </section>

        <section className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-6">
          <h2 className="text-lg font-bold text-white mb-4">Readiness</h2>
          <p className="text-5xl font-bold text-indigo-300">{Math.round(report?.readiness_score ?? analysis?.resume_score ?? 0)}</p>
          <p className="text-sm text-slate-500 mt-2">Current readiness score</p>
          <div className="mt-5 space-y-3 text-sm">
            <p className="text-slate-300">Total sessions: <span className="text-white font-semibold">{analytics?.total_interviews ?? history.length}</span></p>
            <p className="text-slate-300">Average interview score: <span className="text-white font-semibold">{analytics?.average_interview_score ?? 0}</span></p>
            <p className="text-slate-300">Best score: <span className="text-white font-semibold">{analytics?.best_interview_score ?? 0}</span></p>
          </div>
        </section>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <ListPanel title="Strengths" items={strengths} />
        <ListPanel title="Weaknesses" items={weaknesses} />
      </div>

      <section className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-6">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
          <h2 className="text-lg font-bold text-white">Interview Questions</h2>
          <div className="flex gap-2">
            <select value={difficulty} onChange={(e) => setDifficulty(e.target.value as InterviewDifficulty)} className="rounded-xl border border-white/10 bg-[#0d1a35] px-3 py-2 text-sm text-slate-200">
              <option>Easy</option>
              <option>Medium</option>
              <option>Hard</option>
            </select>
            <button onClick={generateQuestions} disabled={generating || !activeSessionId} className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">
              {generating ? "Generating..." : "Generate Questions"}
            </button>
          </div>
        </div>

        {questions.length > 0 ? (
          <div className="grid lg:grid-cols-2 gap-4">
            <div className="space-y-2">
              {questions.map((question) => (
                <button key={question.id} onClick={() => { setSelectedQuestion(question); setEvaluation(null); }} className={`w-full rounded-xl border px-4 py-3 text-left text-sm transition ${selectedQuestion?.id === question.id ? "border-indigo-400/40 bg-indigo-500/15 text-indigo-100" : "border-white/[0.06] bg-white/[0.03] text-slate-300 hover:bg-white/[0.06]"}`}>
                  <p className="font-medium">{question.question}</p>
                  <p className="mt-1 text-xs text-slate-500">{question.category} · {question.difficulty}{question.answered ? " · answered" : ""}</p>
                </button>
              ))}
            </div>
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-4">
              {selectedQuestion ? (
                <>
                  <p className="text-sm font-semibold text-white mb-3">{selectedQuestion.question}</p>
                  <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={7} className="w-full rounded-xl border border-white/10 bg-white/[0.04] p-3 text-sm text-slate-200 outline-none focus:ring-2 focus:ring-indigo-500/40" placeholder="Type your answer..." />
                  <button onClick={evaluateAnswer} disabled={evaluating || !answer.trim()} className="mt-3 w-full rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50">
                    {evaluating ? "Evaluating..." : "Evaluate Answer"}
                  </button>
                  {evaluation && (
                    <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4">
                      <p className="text-2xl font-bold text-emerald-300">{evaluation.score}/100</p>
                      <p className="mt-2 text-sm leading-6 text-slate-300">{evaluation.feedback}</p>
                      <p className="mt-3 text-sm text-slate-400">{evaluation.suggested_improvement}</p>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-slate-500">Select a question to practice.</p>
              )}
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">Upload a resume and generate questions to begin.</p>
        )}
      </section>

      <section className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-6">
        <h2 className="text-lg font-bold text-white mb-4">Session History</h2>
        {history.length > 0 ? (
          <div className="space-y-2">
            {history.slice(0, 6).map((session) => (
              <button key={session.id} onClick={() => refreshInterviewData(session.id)} className="flex w-full items-center justify-between gap-4 rounded-xl border border-white/[0.06] bg-white/[0.03] px-4 py-3 text-left text-sm hover:bg-white/[0.06]">
                <span className="text-slate-300 truncate">{session.resume_name}</span>
                <span className="text-slate-500">{session.question_count} questions · {session.answer_count} answers</span>
              </button>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No interview history yet.</p>
        )}
      </section>
    </div>
  );
}

function ListPanel({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-6">
      <h2 className="text-lg font-bold text-white mb-4">{title}</h2>
      {items.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {items.map((item) => (
            <span key={item} className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-slate-300">{item}</span>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-500">No {title.toLowerCase()} available yet.</p>
      )}
    </section>
  );
}
