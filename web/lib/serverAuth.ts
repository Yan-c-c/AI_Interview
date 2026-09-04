import type { NextRequest, NextResponse } from "next/server";
import type { AuthSession } from "@/lib/auth";
import {
  AUTH_COOKIE_MAX_AGE,
  AUTH_SESSION_COOKIE,
  AUTH_TOKEN_COOKIE,
  serializeSessionCookie,
} from "@/lib/session";

const AUTH_COOKIE_OPTIONS = {
  httpOnly: true,
  sameSite: "lax" as const,
  secure: false,
  path: "/",
};

export function setAuthCookies(response: NextResponse, session: AuthSession) {
  response.cookies.set(AUTH_TOKEN_COOKIE, session.token, {
    ...AUTH_COOKIE_OPTIONS,
    maxAge: AUTH_COOKIE_MAX_AGE,
  });
  response.cookies.set(AUTH_SESSION_COOKIE, serializeSessionCookie(session), {
    ...AUTH_COOKIE_OPTIONS,
    maxAge: AUTH_COOKIE_MAX_AGE,
  });
}

export function clearAuthCookies(response: NextResponse) {
  response.cookies.set(AUTH_TOKEN_COOKIE, "", {
    ...AUTH_COOKIE_OPTIONS,
    maxAge: 0,
  });
  response.cookies.set(AUTH_SESSION_COOKIE, "", {
    ...AUTH_COOKIE_OPTIONS,
    maxAge: 0,
  });
}

export function requestLocalUrl(request: NextRequest, path: string) {
  const protocol = request.headers.get("x-forwarded-proto") || request.nextUrl.protocol.replace(":", "") || "http";
  const host = request.headers.get("host") || request.nextUrl.host;
  return new URL(path, `${protocol}://${host}`);
}

export function requestHostname(request: NextRequest) {
  return (request.headers.get("host") || request.nextUrl.host).split(":")[0];
}
