"use client";

import { useState } from "react";
import { generateQuiz, saveQuizResult, type QuizAnswerDetail } from "@/lib/api";

interface QuizQuestion {
  question: string;
  options: string[];
  correctAnswer: number;
  explanation?: string;
  difficulty?: string;
  topic?: string;
}

interface SavedQuizResult {
  result_id: number;
  score: number;
  total_questions: number;
  percentage: number;
  accuracy: number;
  correct_count: number;
  incorrect_count: number;
  correct_answers: QuizAnswerDetail[];
  incorrect_answers: QuizAnswerDetail[];
  explanations: Array<{
    question: string;
    correct_answer: string;
    explanation: string;
  }>;
  mastery?: {
    mastery_level: string;
    mastery_score: number;
    accuracy: number;
  } | null;
}

export default function QuizCard() {
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("Easy");
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, string>>({});
  const [score, setScore] = useState<number | null>(null);
  const [result, setResult] = useState<SavedQuizResult | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cleanJSON = (str: string): string =>
    str.replace(/```json/g, "").replace(/```/g, "").trim();

  const normalizeQuestion = (raw: any): QuizQuestion | null => {
    const options: string[] = Array.isArray(raw?.options) ? raw.options.map(String) : [];
    if (!raw?.question || options.length === 0) return null;

    const directIndex = Number(raw.correctAnswer ?? raw.correct_answer_index);
    let correctIndex = Number.isInteger(directIndex) ? directIndex : -1;
    const answerText = String(
      raw.answer ?? raw.correct_answer ?? raw.correctAnswerText ?? raw.correct ?? ""
    ).trim();

    if (correctIndex < 0 && answerText) {
      correctIndex = options.findIndex(
        (option) => option.trim().toLowerCase() === answerText.toLowerCase()
      );
    }
    if (correctIndex < 0 || correctIndex >= options.length) correctIndex = 0;

    return {
      question: String(raw.question),
      options,
      correctAnswer: correctIndex,
      explanation: String(
        raw.explanation ?? raw.reason ?? "Review this concept and compare it with the correct answer."
      ),
      difficulty: raw.difficulty,
      topic: raw.topic,
    };
  };

  const handleGenerate = async () => {
    if (!topic.trim()) {
      setError("Please enter a topic before generating a quiz.");
      return;
    }
    setLoading(true);
    setError(null);
    setScore(null);
    setResult(null);
    setSubmitted(false);
    setSelectedAnswers({});
    try {
      const data = await generateQuiz(topic, difficulty, 10);
      const parsed = typeof data.quiz === "string" ? JSON.parse(cleanJSON(data.quiz)) : data.quiz;
      const normalized = (Array.isArray(parsed) ? parsed : [])
        .map(normalizeQuestion)
        .filter((item): item is QuizQuestion => item !== null);
      if (normalized.length === 0) {
        throw new Error("Quiz response did not contain usable questions.");
      }
      setQuestions(normalized);
    } catch (error) {
      console.error("Quiz Error:", error);
      setError(error instanceof Error ? error.message : "Quiz generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const submitQuiz = async () => {
    const answerDetails: QuizAnswerDetail[] = questions.map((q, index) => {
      const selected = selectedAnswers[index] ?? null;
      const expected = q.options[q.correctAnswer];
      return {
        question: q.question,
        selected_answer: selected,
        correct_answer: expected,
        is_correct: selected === expected,
        explanation: q.explanation ?? "Review this concept and compare it with the correct answer.",
      };
    });
    const correct = answerDetails.filter((item) => item.is_correct).length;
    setScore(correct);
    setSubmitted(true);
    setSaving(true);
    setError(null);
    try {
      const saved = await saveQuizResult(topic, correct, questions.length, null, answerDetails);
      setResult(saved);
    } catch (error) {
      console.error("Save quiz result failed:", error);
      setError(error instanceof Error ? error.message : "Quiz was graded, but the result could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  const accuracy = score !== null && questions.length > 0
    ? Math.round((score / questions.length) * 100)
    : null;

  const accuracyColor =
    accuracy === null ? "text-white" :
    accuracy >= 80 ? "text-emerald-400" :
    accuracy >= 50 ? "text-yellow-400" : "text-red-400";

  const getOptionStyle = (q: QuizQuestion, option: string, index: number) => {
    const isSelected = selectedAnswers[index] === option;
    if (!submitted) {
      return isSelected
        ? "bg-blue-500/20 border-blue-500/40 text-blue-300"
        : "bg-white/[0.03] border-white/[0.06] text-slate-300 hover:bg-white/[0.06] hover:border-white/10";
    }
    const isCorrect = option === q.options[q.correctAnswer];
    if (isCorrect) return "bg-emerald-500/20 border-emerald-500/40 text-emerald-300";
    if (isSelected && !isCorrect) return "bg-red-500/20 border-red-500/40 text-red-300";
    return "bg-white/[0.02] border-white/[0.04] text-slate-500";
  };

  return (
    <div className="w-full">
      <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-8 shadow-xl shadow-black/20">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
          <input
            className="bg-white/[0.05] border border-white/10 text-slate-200 placeholder-slate-500 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition"
            placeholder="Enter Topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
          <select
            className="bg-[#0d1a35] border border-white/10 text-slate-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
          >
            <option>Easy</option>
            <option>Medium</option>
            <option>Hard</option>
          </select>
        </div>
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold py-3.5 rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/20"
        >
          {loading ? "Generating..." : "Generate Quiz"}
        </button>
        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}
      </div>

      {questions.length > 0 && (
        <div className="mt-6 space-y-4">
          {questions.map((q, index) => (
            <div
              key={`${q.question}-${index}`}
              className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20"
            >
              <h3 className="font-semibold text-white text-base mb-4">
                <span className="text-blue-400 mr-1.5">Q{index + 1}.</span> {q.question}
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {q.options.map((option, idx) => (
                  <label
                    key={`${option}-${idx}`}
                    className={`flex items-center gap-3 px-4 py-3 rounded-xl cursor-pointer border transition-all duration-150 text-sm ${getOptionStyle(q, option, index)}`}
                  >
                    <input
                      type="radio"
                      name={`question-${index}`}
                      value={option}
                      checked={selectedAnswers[index] === option}
                      onChange={() =>
                        !submitted &&
                        setSelectedAnswers((prev) => ({ ...prev, [index]: option }))
                      }
                      disabled={submitted}
                      className="accent-blue-500 shrink-0"
                    />
                    <span className="min-w-0 flex-1">{option}</span>
                    {submitted && option === q.options[q.correctAnswer] && (
                      <span className="ml-auto shrink-0 text-emerald-400 text-xs font-semibold">Correct</span>
                    )}
                    {submitted && selectedAnswers[index] === option && option !== q.options[q.correctAnswer] && (
                      <span className="ml-auto shrink-0 text-red-400 text-xs font-semibold">Incorrect</span>
                    )}
                  </label>
                ))}
              </div>
              {submitted && (
                <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Explanation</p>
                  <p className="text-sm leading-6 text-slate-300">
                    {q.explanation ?? "Review this concept and compare it with the correct answer."}
                  </p>
                </div>
              )}
            </div>
          ))}

          {!submitted && (
            <button
              onClick={submitQuiz}
              disabled={Object.keys(selectedAnswers).length !== questions.length}
              className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold py-3.5 rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-500/20"
            >
              Submit Quiz
            </button>
          )}
        </div>
      )}

      {submitted && score !== null && (
        <div className="mt-5 bg-white/[0.04] border border-white/[0.08] rounded-2xl p-8 shadow-xl shadow-black/20">
          <h2 className="text-xl font-bold text-white mb-6">Quiz Result</h2>
          <div className="flex flex-wrap gap-8 items-center">
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-widest mb-2">Score</p>
              <p className="text-4xl font-bold text-white">
                {score}
                <span className="text-slate-500 text-xl font-normal">/{questions.length}</span>
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-widest mb-2">Percentage</p>
              <p className={`text-4xl font-bold ${accuracyColor}`}>{accuracy}%</p>
            </div>
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-widest mb-2">Accuracy</p>
              <p className={`text-4xl font-bold ${accuracyColor}`}>{(result?.accuracy ?? accuracy ?? 0).toFixed(1)}%</p>
            </div>
          </div>

          <div className="mt-6 grid md:grid-cols-3 gap-3">
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4">
              <p className="text-xs text-emerald-300/80 uppercase tracking-widest mb-1">Correct Answers</p>
              <p className="text-2xl font-bold text-emerald-300">{result?.correct_count ?? score}</p>
            </div>
            <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4">
              <p className="text-xs text-red-300/80 uppercase tracking-widest mb-1">Incorrect Answers</p>
              <p className="text-2xl font-bold text-red-300">{result?.incorrect_count ?? questions.length - score}</p>
            </div>
            <div className="rounded-xl border border-blue-500/20 bg-blue-500/10 p-4">
              <p className="text-xs text-blue-300/80 uppercase tracking-widest mb-1">Mastery</p>
              <p className="text-lg font-bold text-blue-300">
                {saving ? "Updating..." : result?.mastery?.mastery_level ?? "Updated"}
              </p>
            </div>
          </div>

          <div className="mt-6">
            <div className="w-full bg-white/5 rounded-full h-2.5 overflow-hidden">
              <div
                className={`h-2.5 rounded-full transition-all duration-700 ${
                  (accuracy ?? 0) >= 80 ? "bg-gradient-to-r from-emerald-500 to-teal-400" :
                  (accuracy ?? 0) >= 50 ? "bg-gradient-to-r from-yellow-500 to-amber-400" :
                  "bg-gradient-to-r from-red-500 to-rose-400"
                }`}
                style={{ width: `${accuracy}%` }}
              />
            </div>
          </div>

          {(result?.incorrect_answers?.length ?? 0) > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-white mb-3">Incorrect Answers</h3>
              <div className="space-y-3">
                {result!.incorrect_answers.map((item, index) => (
                  <div key={`${item.question}-${index}`} className="rounded-xl border border-red-500/20 bg-red-500/5 p-4">
                    <p className="text-sm text-slate-200 font-medium">{item.question}</p>
                    <p className="text-xs text-red-300 mt-2">Your answer: {item.selected_answer ?? "Not answered"}</p>
                    <p className="text-xs text-emerald-300 mt-1">Correct answer: {item.correct_answer}</p>
                    <p className="text-sm text-slate-400 mt-3 leading-6">{item.explanation}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={() => {
              setQuestions([]);
              setSelectedAnswers({});
              setScore(null);
              setResult(null);
              setSubmitted(false);
              setTopic("");
              setError(null);
            }}
            className="mt-6 w-full bg-white/[0.05] hover:bg-white/[0.08] border border-white/10 text-slate-300 font-medium py-3 rounded-xl transition-all duration-200"
          >
            Try Another Quiz
          </button>
        </div>
      )}
    </div>
  );
}
