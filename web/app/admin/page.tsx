import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { AdminDashboard } from "@/components/AdminDashboard";
import type { AuthUser } from "@/lib/auth";
import type { AdminOverview, AgentMonitor, AudioReviewTask } from "@/lib/api/admin";
import { AUTH_TOKEN_COOKIE, resolveApiBaseUrl } from "@/lib/session";

export const dynamic = "force-dynamic";

type MeResponse = { success: boolean; user: AuthUser };
type UsersResponse = { success: boolean; users: AuthUser[] };
type AgentsResponse = { success: boolean; agents: AgentMonitor[] };
type AudioTasksResponse = { success: boolean; tasks: AudioReviewTask[] };

export default async function AdminPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_TOKEN_COOKIE)?.value;
  if (!token) redirect("/login");

  const requestHeaders = await headers();
  const hostname = requestHeaders.get("host")?.split(":")[0];
  const apiBaseUrl = resolveApiBaseUrl(hostname);

  let currentUser: AuthUser;
  try {
    const me = await requestJson<MeResponse>(apiBaseUrl, "/api/admin/auth/me", token);
    currentUser = me.user;
  } catch {
    redirect("/login?error=登录状态无效，请重新登录。");
  }

  if (currentUser.role !== "admin") {
    return <AdminDashboard initialUser={currentUser} initialForbidden />;
  }

  const [overviewResult, usersResult, agentsResult, audioResult] = await Promise.allSettled([
    requestJson<AdminOverview>(apiBaseUrl, "/api/admin/overview", token),
    requestJson<UsersResponse>(apiBaseUrl, "/api/admin/users", token),
    requestJson<AgentsResponse>(apiBaseUrl, "/api/admin/agent-monitoring", token),
    requestJson<AudioTasksResponse>(apiBaseUrl, "/api/admin/audio-reviews", token),
  ]);

  const initialMessage =
    [overviewResult, usersResult, agentsResult, audioResult].some((result) => result.status === "rejected")
      ? "部分后台数据暂时无法读取，已先展示可用数据。请确认后端服务正常运行后刷新。"
      : "";

  return (
    <AdminDashboard
      initialUser={currentUser}
      initialOverview={overviewResult.status === "fulfilled" ? overviewResult.value : null}
      initialUsers={usersResult.status === "fulfilled" ? usersResult.value.users : []}
      initialAgents={agentsResult.status === "fulfilled" ? agentsResult.value.agents : []}
      initialAudioTasks={audioResult.status === "fulfilled" ? audioResult.value.tasks : []}
      initialMessage={initialMessage}
    />
  );
}

async function requestJson<T>(apiBaseUrl: string, path: string, token: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail?.message || payload.message || "后台接口请求失败");
  }
  return payload as T;
}
