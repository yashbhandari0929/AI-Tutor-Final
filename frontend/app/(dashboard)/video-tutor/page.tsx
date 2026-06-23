"use client";

// app/dashboard/video-tutor/page.tsx
//
// Extracted from the old AI Tutor page, now its own sidebar item/route.
// Logic unchanged — still calls GET /videos via lib/api.ts searchVideos().

import { useState } from "react";
import { searchVideos } from "@/lib/api";
import { PlayCircle, Search } from "lucide-react";

interface VideoResult {
  videoId: string;
  title: string;
  thumbnail: string;
  channel: string;
}

export default function VideoTutorPage() {
  const [topic, setTopic] = useState("");
  const [videos, setVideos] = useState<VideoResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState<VideoResult | null>(null);

  async function handleSearch() {
    if (!topic.trim()) return;
    setLoading(true);
    try {
      const data = await searchVideos(topic.trim());
      setVideos(data.videos || []);
      setActive(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#060d1f] px-8 py-8">
      <div className="pointer-events-none fixed -top-40 -left-40 w-[500px] h-[500px] rounded-full bg-blue-600/10 blur-[120px]" />
      <div className="pointer-events-none fixed bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-indigo-700/10 blur-[90px]" />

      <div className="max-w-5xl mx-auto relative space-y-8">
        <div>
          <h1 className="mb-2 flex items-center gap-2.5 text-3xl font-bold text-white">
            <PlayCircle size={26} /> Video Tutor
          </h1>
          <p className="text-sm text-slate-500">Find explainer videos for any topic you're stuck on.</p>
        </div>

        <div className="flex max-w-xl items-center gap-3 rounded-2xl border border-white/[0.08] bg-white/[0.04] px-4 py-3 shadow-xl shadow-black/20">
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Enter topic"
            className="flex-1 bg-transparent text-sm text-slate-200 outline-none placeholder-slate-500"
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-xl bg-red-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-red-500 disabled:opacity-50 transition-colors shrink-0"
          >
            <Search size={15} /> {loading ? "Searching…" : "Search"}
          </button>
        </div>

        {active && (
          <div className="aspect-video max-w-3xl overflow-hidden rounded-2xl border border-white/[0.08] shadow-xl shadow-black/20">
            <iframe
              className="h-full w-full"
              src={`https://www.youtube.com/embed/${active.videoId}`}
              title={active.title}
              allowFullScreen
            />
          </div>
        )}

        {videos.length > 0 && (
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {videos.map((v) => (
              <button
                key={v.videoId}
                onClick={() => setActive(v)}
                className="overflow-hidden rounded-2xl border border-white/[0.08] bg-white/[0.04] text-left shadow-xl shadow-black/20 hover:bg-white/[0.07] transition-colors"
              >
                <img src={v.thumbnail} alt={v.title} className="aspect-video w-full object-cover" />
                <div className="p-5">
                  <p className="line-clamp-2 text-sm font-medium text-slate-200">{v.title}</p>
                  <p className="mt-1.5 text-xs text-slate-500">{v.channel}</p>
                </div>
              </button>
            ))}
          </div>
        )}

        {!loading && videos.length === 0 && (
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.04] p-10 text-center shadow-xl shadow-black/20">
            <p className="text-sm text-slate-500">Search a topic above to see videos here.</p>
          </div>
        )}
      </div>
    </div>
  );
}