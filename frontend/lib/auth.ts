// lib/auth.ts
// localStorage-based session + JWT management

export interface StudentSession {
  student_id: number | null;
  name: string;
  email: string;
  token: string; // ← NEW: JWT access token returned by /auth/login and /auth/register
}

const SESSION_KEY = "ai_tutor_session";

export function saveSession(data: StudentSession) {
  if (typeof window !== "undefined") {
    localStorage.setItem(SESSION_KEY, JSON.stringify(data));
  }
}

export function getSession(): StudentSession | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StudentSession;
  } catch {
    return null;
  }
}

export function clearSession() {
  if (typeof window !== "undefined") {
    localStorage.removeItem(SESSION_KEY);
  }
}

export function isLoggedIn(): boolean {
  return getSession() !== null;
}

// ── NEW ──────────────────────────────────────────────────────────────────────

/** Returns the JWT access token, or null if not logged in. */
export function getToken(): string | null {
  return getSession()?.token ?? null;
}

/**
 * True if a session with a token exists. Does NOT verify the token is
 * still valid/unexpired with the backend — that's checked server-side on
 * each protected request. This is a client-side "do we have a session at
 * all" check, used for routing decisions.
 */
export function isAuthenticated(): boolean {
  return !!getToken();
}

/** Clears the session and sends the user to /login. */
export function logout(): void {
  clearSession();
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}