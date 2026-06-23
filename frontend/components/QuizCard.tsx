"use client";

import { useState } from "react";
import { generateQuiz, saveQuizResult } from "@/lib/api";

interface QuizQuestion {
  question: string;
  options: string[];
  correctAnswer: number;
  difficulty?: string;
  topic?: string;
}

export default function QuizCard() {
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("Easy");
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [selectedAnswers, setSelectedAnswers] = useState<{ [key: number]: string }>({});
  const [score, setScore] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const cleanJSON = (str: string): string => {
    return str.replace(/```json/g, "").replace(/```/g, "").trim();
  };

  const handleGenerate = async () => {
    setLoading(true);
    setScore(null);
    setSubmitted(false);
    setSelectedAnswers({});
    try {
      const data = await generateQuiz(topic, difficulty, 10);
      console.log("QUIZ RESPONSE:", data.quiz);
      let parsed;
      if (typeof data.quiz === "string") {
        const cleaned = cleanJSON(data.quiz);
        parsed = JSON.parse(cleaned);
      } else {
        parsed = data.quiz;
      }
      setQuestions(parsed);
    } catch (error) {
      console.error("Quiz Error:", error);
      alert("Quiz generation failed");
    } finally {
      setLoading(false);
    }
  };

  const submitQuiz = async () => {
    let correct = 0;
    questions.forEach((q, index) => {
      const selected = selectedAnswers[index];
      const expected = q.options[q.correctAnswer];
      console.log(`Q${index + 1}: selected="${selected}" expected="${expected}" match=${selected === expected}`);
      if (selected === expected) correct++;
    });
    console.log("FINAL SCORE:", correct, "/", questions.length);
    setScore(correct);
    setSubmitted(true);
    await saveQuizResult(topic, correct, questions.length);
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
    // After submit: show correct/wrong
    const isCorrect = option === q.options[q.correctAnswer];
    if (isCorrect) return "bg-emerald-500/20 border-emerald-500/40 text-emerald-300";
    if (isSelected && !isCorrect) return "bg-red-500/20 border-red-500/40 text-red-300";
    return "bg-white/[0.02] border-white/[0.04] text-slate-500";
  };

  return (
    <div className="w-full">
      {/* Controls */}
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
          {loading ? "Generating…" : "Generate Quiz"}
        </button>
      </div>

      {/* Questions */}
      {questions.length > 0 && (
        <div className="mt-6 space-y-4">
          {questions.map((q, index) => (
            <div
              key={index}
              className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20"
            >
              <h3 className="font-semibold text-white text-base mb-4">
                <span className="text-blue-400 mr-1.5">Q{index + 1}.</span> {q.question}
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {q.options.map((option, idx) => (
                  <label
                    key={idx}
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
                    {option}
                   {submitted && option === q.options[q.correctAnswer] && ( 
                      <span className="ml-auto text-emerald-400 text-xs font-semibold">✓ Correct</span>
                    )}
                  </label>
                ))}
              </div>
            </div>
          ))}

          {!submitted && (
            <button
              onClick={submitQuiz}
              className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold py-3.5 rounded-xl transition-all duration-200 shadow-lg shadow-emerald-500/20"
            >
              Submit Quiz
            </button>
          )}
        </div>
      )}

      {/* Result */}
      {submitted && score !== null && (
        <div className="mt-5 bg-white/[0.04] border border-white/[0.08] rounded-2xl p-8 shadow-xl shadow-black/20">
          <h2 className="text-xl font-bold text-white mb-6">Quiz Result</h2>
          <div className="flex gap-10 items-center">
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-widest mb-2">Score</p>
              <p className="text-4xl font-bold text-white">
                {score}
                <span className="text-slate-500 text-xl font-normal">/{questions.length}</span>
              </p>
            </div>
            <div className="w-px h-16 bg-white/[0.08]" />
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-widest mb-2">Accuracy</p>
              <p className={`text-4xl font-bold ${accuracyColor}`}>{accuracy}%</p>
            </div>
            <div className="w-px h-16 bg-white/[0.08]" />
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-widest mb-2">Wrong</p>
              <p className="text-4xl font-bold text-red-400">{questions.length - score}</p>
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-6">
            <div className="w-full bg-white/5 rounded-full h-2.5 overflow-hidden">
              <div
                className={`h-2.5 rounded-full transition-all duration-700 ${
                  accuracy! >= 80 ? "bg-gradient-to-r from-emerald-500 to-teal-400" :
                  accuracy! >= 50 ? "bg-gradient-to-r from-yellow-500 to-amber-400" :
                  "bg-gradient-to-r from-red-500 to-rose-400"
                }`}
                style={{ width: `${accuracy}%` }}
              />
            </div>
          </div>

          <button
            onClick={() => {
              setQuestions([]);
              setSelectedAnswers({});
              setScore(null);
              setSubmitted(false);
              setTopic("");
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