// LOCATION: app/(dashboard)/notes/page.tsx

"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { generateNotes } from "@/lib/api";
import { getSession } from "@/lib/auth";

export default function NotesPage() {
  useAuth();

  const [subject, setSubject] = useState("");
  const [topic, setTopic] = useState("");
  const [level, setLevel] = useState("Beginner");
  const [length, setLength] = useState("Short");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    if (!topic.trim()) { alert("Please enter a topic"); return; }
    setLoading(true);
    try {
      const session = getSession();
      const data = await generateNotes(
        subject,
        topic,
        level,
        length,
        session?.student_id ?? null,   // ← pass student_id so the topic gets saved
      );
      setNotes(data.notes || "No notes generated.");
    } catch (error) {
      console.error(error);
      setNotes("Failed to generate notes.");
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#060d1f] px-8 py-8">
      <div className="pointer-events-none fixed -top-40 -left-40 w-[500px] h-[500px] rounded-full bg-blue-600/10 blur-[120px]" />
      <div className="pointer-events-none fixed bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-indigo-700/10 blur-[90px]" />

      <div className="max-w-4xl mx-auto relative">
        <h1 className="text-3xl font-bold text-white mb-8">AI Notes Generator</h1>

        <div className="bg-white/[0.04] backdrop-blur border border-white/[0.08] rounded-2xl p-8 shadow-xl shadow-black/20">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            <input
              type="text"
              placeholder="Subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="bg-white/[0.05] border border-white/10 text-slate-200 placeholder-slate-500 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition"
            />
            <input
              type="text"
              placeholder="Topic"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="bg-white/[0.05] border border-white/10 text-slate-200 placeholder-slate-500 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition"
            />
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              className="bg-[#0d1a35] border border-white/10 text-slate-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition"
            >
              <option>Beginner</option>
              <option>Intermediate</option>
              <option>Advanced</option>
            </select>
            <select
              value={length}
              onChange={(e) => setLength(e.target.value)}
              className="bg-[#0d1a35] border border-white/10 text-slate-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition"
            >
              <option>Short</option>
              <option>Medium</option>
              <option>Detailed</option>
            </select>
          </div>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold py-3.5 rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/20 mt-2"
          >
            {loading ? "Generating…" : "Generate Notes"}
          </button>
        </div>

        {notes && (
          <div className="mt-6 bg-white/[0.04] backdrop-blur border border-white/[0.08] rounded-2xl p-8 shadow-xl shadow-black/20">
            <h2 className="text-xl font-bold text-white mb-5">Generated Notes</h2>
            <div className="notes-body" dangerouslySetInnerHTML={{ __html: notes }} />
          </div>
        )}
      </div>

      <style>{`
        .notes-body { color: #cbd5e1; line-height: 1.8; font-size: 0.95rem; }
        .notes-body .notes-h1 { font-size: 1.5rem; font-weight: 700; margin: 1.5rem 0 0.75rem; color: #f1f5f9; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 0.5rem; }
        .notes-body .notes-h2 { font-size: 1.2rem; font-weight: 700; margin: 1.5rem 0 0.5rem; color: #60a5fa; border-left: 3px solid #3b82f6; padding-left: 0.75rem; }
        .notes-body .notes-h3 { font-size: 1rem; font-weight: 600; margin: 1.25rem 0 0.4rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; }
        .notes-body .notes-ul { list-style: none; margin: 0.5rem 0 0.75rem 0; padding: 0; }
        .notes-body .notes-li { position: relative; padding: 0.3rem 0 0.3rem 1.5rem; border-left: 2px solid rgba(59,130,246,0.25); margin-bottom: 0.3rem; color: #cbd5e1; }
        .notes-body .notes-li::before { content: "→"; position: absolute; left: 0.35rem; color: #3b82f6; font-size: 0.8rem; top: 0.4rem; }
        .notes-body .notes-bold { font-weight: 700; color: #f1f5f9; }
        .notes-body .notes-code { background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; padding: 0.1rem 0.4rem; font-family: monospace; font-size: 0.875rem; color: #f87171; }
      `}</style>
    </div>
  );
}