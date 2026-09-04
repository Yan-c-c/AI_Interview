export type UserRole = "user" | "admin";
export type UserStatus = "active" | "disabled";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  created_at?: string;
  updated_at?: string;
  last_login_at?: string | null;
}

export interface AuthSession {
  token: string;
  user: AuthUser;
}

const AUTH_STORAGE_KEY = "ai_interview_auth_session";

export function getAuthSession(): AuthSession | null {
  if (typeof window === "undefined") return null;
  const raw = safeLocalStorage()?.getItem(AUTH_STORAGE_KEY);
  if (!raw) return null;
  try {
    const data = JSON.parse(raw) as AuthSession;
    if (!data?.token || !data?.user) return null;
    return data;
  } catch {
    clearAuthSession();
    return null;
  }
}

export function saveAuthSession(session: AuthSession) {
  if (typeof window === "undefined") return;
  safeLocalStorage()?.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

export function clearAuthSession() {
  if (typeof window === "undefined") return;
  safeLocalStorage()?.removeItem(AUTH_STORAGE_KEY);
}

export function authHeaders(): Record<string, string> {
  const session = getAuthSession();
  return session?.token ? { Authorization: `Bearer ${session.token}` } : {};
}

function safeLocalStorage(): Storage | null {
  try {
    return window.localStorage ?? null;
  } catch {
    return null;
  }
}
