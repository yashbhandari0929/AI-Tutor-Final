"use client";

// app/dashboard/flashcards/page.tsx
//
// Extracted from the old AI Tutor page, now its own sidebar item/route.
// Adds a topic input (the old page only had a bare "Generate Flashcards"
// button with no visible field to type a topic into — assumed it asked
// for one elsewhere; wire this up to however your flow actually captured
// topic if that assumption's wrong).

import { useState } from "react";
import { generateFlashcards, FlashcardItem } from "@/lib/api";
import { Brain, Sparkles } from "lucide-react";

export default function FlashcardsPage() {
  const [topic, setTopic] = useState("");
  const [cards, setCards] = useState<FlashcardItem[]>([]);
  const [flipped, setFlipped] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(false);

  async function handleGenerate() {
    if (!topic.trim()) return;
    setLoading(true);
    setFlipped(new Set());
    try {
      const result = await generateFlashcards(topic.trim());
      setCards(result);
    } finally {
      setLoading(false);
    }
  }

  function toggleFlip(i: number) {
    setFlipped((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  return (
    <div className="min-h-screen bg-[#060d1f] px-8 py-8">
      <div className="pointer-events-none fixed -top-40 -left-40 w-[500px] h-[500px] rounded-full bg-blue-600/10 blur-[120px]" />
      <div className="pointer-events-none fixed bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-indigo-700/10 blur-[90px]" />

      <div className="max-w-5xl mx-auto relative space-y-8">
        <div>
          <h1 className="mb-2 flex items-center gap-2.5 text-3xl font-bold text-white">
            <Brain size={26} /> Flashcards
          </h1>
          <p className="text-sm text-slate-500">Generate quick-review flashcards for any topic.</p>
        </div>

        <div className="flex max-w-xl items-center gap-3 rounded-2xl border border-white/[0.08] bg-white/[0.04] px-4 py-3 shadow-xl shadow-black/20">
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
            placeholder="Enter a topic, e.g. Newton's Laws"
            className="flex-1 bg-transparent text-sm text-slate-200 outline-none placeholder-slate-500"
          />
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50 transition-colors shrink-0"
          >
            <Sparkles size={15} /> {loading ? "Generating…" : "Generate Flashcards"}
          </button>
        </div>

        {cards.length > 0 && (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {cards.map((card, i) => (
              <button
                key={i}
                onClick={() => toggleFlip(i)}
                className="min-h-[170px] rounded-2xl border border-white/[0.08] bg-white/[0.04] p-6 text-left shadow-xl shadow-black/20 hover:bg-white/[0.07] transition-colors"
              >
                <p className="mb-3 text-[11px] font-medium uppercase tracking-widest text-slate-500">
                  {flipped.has(i) ? "Answer" : "Question"} · tap to flip
                </p>
                <p className="text-[15px] leading-relaxed text-slate-200">
                  {flipped.has(i) ? card.answer : card.question}
                </p>
              </button>
            ))}
          </div>
        )}

        {!loading && cards.length === 0 && (
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-10 text-center shadow-xl shadow-black/20">
            <p className="text-sm text-slate-500">Enter a topic above to generate your first set.</p>
          </div>
        )}
      </div>
    </div>
  );
}