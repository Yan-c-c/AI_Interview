import { NextRequest, NextResponse } from "next/server";
import type { AuthSession } from "@/lib/auth";
import { resolveApiBaseUrl } from "@/lib/session";
import { requestHostname, requestLocalUrl, setAuthCookies } from "@/lib/serverAuth";

type LoginResponse = AuthSession & { success: boolean };

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const email = String(formData.get("email") || "");
  const password = String(formData.get("password") || "");
  const apiBaseUrl = resolveApiBaseUrl(requestHostname(request));

  try {
    const session = await postJson<LoginResponse>(apiBaseUrl, "/api/admin/auth/login", { email, password });
    const targetPath = session.user.role === "admin" ? "/admin" : "/";
    const response = NextResponse.redirect(requestLocalUrl(request, targetPath), { status: 303 });
    setAuthCookies(response, { token: session.token, user: session.user });
    return response;
  } catch (error) {
    return redirectWithError(request, "/login", error instanceof Error ? error.message : "登录失败");
  }
}

async function postJson<T>(apiBaseUrl: string, path: string, body: Record<string, string>): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail?.message || payload.message || "登录失败，请确认后端服务已启动。");
  }
  return payload as T;
}

function redirectWithError(request: NextRequest, path: string, message: string) {
  const url = requestLocalUrl(request, path);
  url.searchParams.set("error", message);
  return NextResponse.redirect(url, { status: 303 });
}
