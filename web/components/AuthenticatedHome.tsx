"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { clearAuthSession, getAuthSession, saveAuthSession, type AuthUser } from "@/lib/auth";
import { fetchMe } from "@/lib/api/admin";
import { AssistantChat } from "./AssistantChat";

export function AuthenticatedHome({ initialUser = null }: { initialUser?: AuthUser | null }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(initialUser);
  const [checking, setChecking] = useState(!initialUser);

  useEffect(() => {
    if (initialUser) {
      setUser(initialUser);
      setChecking(false);
      return;
    }

    const session = getAuthSession();
    if (!session) {
      router.replace("/login");
      return;
    }
    setUser(session.user);
    fetchMe()
      .then((response) => {
        saveAuthSession({ token: session.token, user: response.user });
        setUser(response.user);
      })
      .catch(() => {
        clearAuthSession();
        router.replace("/login");
      })
      .finally(() => setChecking(false));
  }, [router]);

  function handleSignOut() {
    clearAuthSession();
    window.location.href = "/logout";
  }

  if (checking || !user) {
    return (
      <main className="auth-loading">
        <Loader2 className="spin-icon" size={22} />
        <span>正在验证登录状态...</span>
      </main>
    );
  }

  return <AssistantChat currentUser={user} onSignOut={handleSignOut} />;
}
