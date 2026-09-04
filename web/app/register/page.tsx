import Link from "next/link";
import { Bot, UserPlus } from "lucide-react";

type PageProps = {
  searchParams?: Promise<{ error?: string | string[] }>;
};

export default async function RegisterPage({ searchParams }: PageProps) {
  const params = searchParams ? await searchParams : {};
  const message = typeof params.error === "string" ? params.error : "";

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand">
          <div className="auth-brand-icon"><Bot size={24} /></div>
          <div>
            <h1>创建账号</h1>
            <p>注册后进入用户工作台。管理员账号由后台用户管理分配。</p>
          </div>
        </div>

        <form className="auth-form" action="/api/auth/register" method="post">
          <label>
            姓名
            <input name="name" autoComplete="name" required />
          </label>
          <label>
            邮箱
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label>
            密码
            <input name="password" type="password" autoComplete="new-password" placeholder="至少 6 位" minLength={6} required />
          </label>
          {message && <div className="auth-message">{message}</div>}
          <button type="submit" className="auth-submit">
            <UserPlus size={18} />
            注册并进入
          </button>
        </form>

        <div className="auth-foot">
          <span>已有账号？</span>
          <Link href="/login">返回登录</Link>
        </div>
      </section>
    </main>
  );
}
