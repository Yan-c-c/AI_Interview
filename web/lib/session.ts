import type { AuthSession } from "@/lib/auth";

export const AUTH_SESSION_COOKIE = "ai_interview_auth_session";
export const AUTH_TOKEN_COOKIE = "ai_interview_auth_token";
export const AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7;

export function resolveApiBaseUrl(hostname?: string | null) {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  const host = hostname && hostname !== "0.0.0.0" ? hostname : "127.0.0.1";
  return `http://${host}:8000`;
}

export function parseSessionCookie(value?: string): AuthSession | null {
  if (!value) return null;
  try {
    const session = JSON.parse(decodeURIComponent(value)) as AuthSession;
    if (!session?.token || !session?.user) return null;
    return session;
  } catch {
    return null;
  }
}

export function serializeSessionCookie(session: AuthSession) {
  return encodeURIComponent(JSON.stringify(session));
}
