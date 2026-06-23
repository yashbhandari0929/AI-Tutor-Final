"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getSession, clearSession, type StudentSession } from "@/lib/auth";

export default function Navbar() {
  const router = useRouter();
  const [session, setSession] = useState<StudentSession | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setSession(getSession());
  }, []);

  const handleLogout = () => {
    clearSession();
    router.push("/login");
  };

  const initials = session?.name
    ? session.name
        .split(" ")
        .map((w) => w[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "?";

  return (
    <div className="h-16 border-b border-white/[0.07] bg-[#060d1f]/80 backdrop-blur-xl flex items-center justify-between px-6 sticky top-0 z-50">
      {/* Logo */}
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow shadow-blue-500/30">
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        </div>
        <span className="text-white font-bold text-base tracking-tight">AI Tutor</span>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {!mounted ? null : session ? (
          <>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-xs font-bold shadow shadow-blue-500/30">
                {initials}
              </div>
              <span className="text-slate-300 text-sm font-medium hidden sm:block">
                {session.name}
              </span>
            </div>

            <div className="h-5 w-px bg-white/10 hidden sm:block" />

            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-slate-400 hover:text-red-400 text-sm font-medium transition-colors duration-150 group"
            >
              <svg
                className="w-4 h-4 transition-transform duration-150 group-hover:translate-x-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                />
              </svg>
              <span className="hidden sm:block">Logout</span>
            </button>
          </>
        ) : (
          <span className="text-slate-500 text-sm">Not signed in</span>
        )}
      </div>
    </div>
  );
}