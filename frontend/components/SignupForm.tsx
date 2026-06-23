"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { saveSession } from "@/lib/auth";

declare global {
  interface Window {
    google: {
      accounts: {
        id: {
          initialize: (config: object) => void;
          renderButton: (element: HTMLElement, config: object) => void;
        };
      };
    };
  }
}

export default function SignupForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

  // ── Google Identity Services setup ────────────────────────────────────────
  useEffect(() => {
    const scriptId = "gis-script";

    const initializeGIS = () => {
      if (!window.google) return;
      window.google.accounts.id.initialize({
        client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!,
        callback: handleGoogleCredential,
      });

      const btn = document.getElementById("google-signup-btn");
      if (btn) {
        window.google.accounts.id.renderButton(btn, {
          theme: "filled_black",
          size: "large",
          width: btn.offsetWidth || 400,
          text: "signup_with",
          shape: "rectangular",
        });
      }
    };

    if (document.getElementById(scriptId)) {
      initializeGIS();
      return;
    }

    const script = document.createElement("script");
    script.id = scriptId;
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = initializeGIS;
    document.body.appendChild(script);
  }, []);

  const handleGoogleCredential = async (response: { credential: string }) => {
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API}/auth/google`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential: response.credential }),
      });

      if (res.ok) {
        const data = await res.json();
        saveSession({
          student_id: data.student_id,
          name: data.name,
          email: data.email,
          token: data.access_token,
        });
        setSuccess(true);
        setTimeout(() => router.push("/dashboard"), 1500);
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data?.detail || "Google sign-in failed. Please try again.");
      }
    } catch {
      setError("Cannot reach the server. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  // ── Email/password signup (unchanged) ────────────────────────────────────
  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      });

      if (response.ok) {
        const data = await response.json();
        saveSession({
          student_id: data.student_id ?? null,
          name: data.name ?? name,
          email: data.email ?? email,
          token: data.access_token,
        });
        setSuccess(true);
        setTimeout(() => router.push("/dashboard"), 1500);
      } else {
        const data = await response.json().catch(() => ({}));
        setError(data?.detail || "Could not create account. Please try again.");
      }
    } catch {
      setError("Cannot reach the server. Please check your connection or try again.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="flex flex-col items-center gap-4 py-6 text-center">
        <div className="w-14 h-14 rounded-full bg-green-500/15 border border-green-500/30 flex items-center justify-center">
          <svg className="w-7 h-7 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div>
          <p className="text-white font-semibold text-lg">Account created!</p>
          <p className="text-slate-400 text-sm mt-1">Taking you to your dashboard…</p>
        </div>
        <div className="w-full bg-white/10 rounded-full h-1 overflow-hidden">
          <div className="bg-blue-500 h-1 rounded-full" style={{ animation: "progress 1.5s linear forwards" }} />
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSignup} className="space-y-5">
      {error && (
        <div className="bg-red-500/10 border border-red-400/30 text-red-300 text-sm px-4 py-3 rounded-xl">
          {error}
        </div>
      )}

      <div className="space-y-1.5">
        <label className="block text-sm font-medium text-slate-300">Full name</label>
        <input
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Alex Johnson"
          className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60 focus:border-blue-500/40 transition-all duration-200 text-sm"
        />
      </div>

      <div className="space-y-1.5">
        <label className="block text-sm font-medium text-slate-300">Email address</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60 focus:border-blue-500/40 transition-all duration-200 text-sm"
        />
      </div>

      <div className="space-y-1.5">
        <label className="block text-sm font-medium text-slate-300">Password</label>
        <input
          type="password"
          required
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Min. 6 characters"
          className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60 focus:border-blue-500/40 transition-all duration-200 text-sm"
        />
      </div>

      <div className="space-y-1.5">
        <label className="block text-sm font-medium text-slate-300">Confirm password</label>
        <input
          type="password"
          required
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder="Re-enter your password"
          className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/60 focus:border-blue-500/40 transition-all duration-200 text-sm"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all duration-200 shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 hover:-translate-y-0.5 active:translate-y-0 text-sm"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            Creating account…
          </span>
        ) : (
          "Create account"
        )}
      </button>

      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-white/10" />
        <span className="text-xs text-slate-500">or continue with</span>
        <div className="flex-1 h-px bg-white/10" />
      </div>

      {/* GIS renders the real Google button into this div */}
      <div id="google-signup-btn" className="w-full flex justify-center" />
    </form>
  );
}