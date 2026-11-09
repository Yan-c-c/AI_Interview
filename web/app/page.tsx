import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { AuthenticatedHome } from "@/components/AuthenticatedHome";
import type { AuthUser } from "@/lib/auth";
import { AUTH_TOKEN_COOKIE, resolveApiBaseUrl } from "@/lib/session";

export const dynamic = "force-dynamic";

type MeResponse = { success: boolean; user: AuthUser };

export default async function Home() {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_TOKEN_COOKIE)?.value;
  if (!token) redirect("/login");

  const requestHeaders = await headers();
  const hostname = requestHeaders.get("host")?.split(":")[0];
  const apiBaseUrl = resolveApiBaseUrl(hostname);

  try {
    const me = await requestJson<MeResponse>(apiBaseUrl, "/api/admin/auth/me", token);
    return <AuthenticatedHome initialUser={me.user} />;
  } catch {
    redirect("/login?error=登录状态无效，请重新登录。");
  }
}

async function requestJson<T>(apiBaseUrl: string, path: string, token: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail?.message || payload.message || "登录状态校验失败");
  }
  return payload as T;
}
