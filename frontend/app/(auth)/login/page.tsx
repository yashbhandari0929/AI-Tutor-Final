"use client";

import LoginForm from "@/components/LoginForm";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

const features = [
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    title: "AI Notes",
    desc: "Auto-generated notes tailored to your level and subject.",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
    title: "Adaptive Quizzes",
    desc: "Smart quizzes that adjust to your strengths and gaps.",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    title: "Learning Analytics",
    desc: "Heatmaps and accuracy trends to guide your study plan.",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    ),
    title: "AI Tutor Chat",
    desc: "Ask anything, get instant explanations from your AI tutor.",
  },
];

// CHANGED: needs to be a client component now so useAuth() (a hook) can run
// in it. The rest of the file — markup, copy, styling — is unchanged.
export default function LoginPage() {
  // Redirects to /dashboard automatically if a session already exists
  // (the "redirect authenticated users away from /login" half of useAuth).
  useAuth();

  return (
    <div className="min-h-screen bg-[#060d1f] flex">

      {/* Left hero panel */}
      <div className="hidden lg:flex flex-col justify-between w-[55%] px-16 py-14 relative overflow-hidden">
        <div className="pointer-events-none absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-blue-600/20 blur-[120px]" />
        <div className="pointer-events-none absolute bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-indigo-700/15 blur-[90px]" />

        <div className="relative flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <span className="text-white font-bold text-lg tracking-tight">AI Tutor</span>
        </div>

        <div className="relative space-y-7 max-w-xl">
          <p className="text-blue-400 text-xs font-semibold tracking-[0.2em] uppercase">Personalised Learning</p>
          <h1 className="text-5xl xl:text-6xl font-extrabold text-white leading-[1.08] tracking-tight">
            Your Personal<br />
            <span className="bg-gradient-to-r from-blue-400 via-blue-300 to-indigo-400 bg-clip-text text-transparent">
              AI Tutor
            </span>
          </h1>
          <p className="text-slate-400 text-lg leading-relaxed">
            Study smarter with AI-generated notes, adaptive quizzes, and a tutor that never sleeps.
          </p>
          <div className="grid grid-cols-2 gap-3 pt-2">
            {features.map((f) => (
              <div key={f.title} className="flex items-start gap-3 bg-white/[0.04] hover:bg-white/[0.07] border border-white/[0.07] rounded-2xl px-4 py-3.5 transition-colors duration-200">
                <div className="mt-0.5 shrink-0 text-blue-400">{f.icon}</div>
                <div>
                  <p className="text-white text-sm font-semibold">{f.title}</p>
                  <p className="text-slate-500 text-xs leading-relaxed mt-0.5">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-slate-600 text-xs">© {new Date().getFullYear()} AI Tutor — built for curious minds.</p>
      </div>

      {/* Right login panel */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 relative">
        <div className="absolute top-8 left-6 flex items-center gap-2 lg:hidden">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <span className="text-white font-bold">AI Tutor</span>
        </div>

        <div className="w-full max-w-md">
          <div className="bg-white/[0.04] backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl shadow-black/40">
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-white">Welcome back!</h2>
              <p className="text-slate-400 text-sm mt-1">Sign in to continue learning.</p>
            </div>
            <LoginForm />
            <p className="mt-6 text-center text-xs text-slate-500">
              Don&apos;t have an account?{" "}
              <Link href="/signup" className="text-blue-400 hover:text-blue-300 transition-colors">
                Get started free
              </Link>
            </p>
          </div>
        </div>
      </div>

    </div>
  );
}