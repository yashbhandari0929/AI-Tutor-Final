"use client";

import { useState } from "react";
import { generateNotes } from "@/lib/api";

export default function NotesCard() {
  const [subject, setSubject] = useState("");
  const [topic, setTopic] = useState("");
  const [level, setLevel] = useState("Beginner");
  const [length, setLength] = useState("Short");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    if (!topic) { alert("Enter topic"); return; }
    setLoading(true);
    setNotes("");
    try {
      const data = await generateNotes(subject, topic, level, length);
      if (!data || !data.notes) {
        setNotes("No notes generated. Try again.");
        return;
      }
      setNotes(data.notes);
    } catch (error) {
      console.error(error);
      setNotes("Failed to generate notes. Check backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
        <input
          type="text"
          placeholder="Subject"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="w-full mb-4 bg-white/[0.05] border border-white/10 text-slate-200 placeholder-slate-500 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition"
        />
        <input
          type="text"
          placeholder="Topic"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          className="w-full mb-4 bg-white/[0.05] border border-white/10 text-slate-200 placeholder-slate-500 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition"
        />
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          className="w-full mb-4 bg-[#0d1a35] border border-white/10 text-slate-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition"
        >
          <option>Beginner</option>
          <option>Intermediate</option>
          <option>Advanced</option>
        </select>
        <select
          value={length}
          onChange={(e) => setLength(e.target.value)}
          className="w-full mb-5 bg-[#0d1a35] border border-white/10 text-slate-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition"
        >
          <option>Short</option>
          <option>Medium</option>
          <option>Long</option>
        </select>
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold py-3 rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/20"
        >
          {loading ? "Generating…" : "Generate Notes"}
        </button>
      </div>

      {notes && (
        <div className="mt-5 bg-white/[0.04] border border-white/[0.08] rounded-2xl p-6 shadow-xl shadow-black/20">
          <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">{notes}</p>
        </div>
      )}
    </div>
  );
}