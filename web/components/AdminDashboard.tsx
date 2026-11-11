"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  BarChart3,
  BookOpen,
  Bot,
  CheckCircle2,
  Database,
  FileAudio,
  Loader2,
  LogOut,
  RefreshCcw,
  Search,
  Send,
  ShieldCheck,
  Trash2,
  Upload,
  UserPlus,
  UsersRound,
} from "lucide-react";
import { clearAuthSession, getAuthSession, saveAuthSession, type AuthUser } from "@/lib/auth";
import {
  AdminOverview,
  AudioReviewTask,
  createAdminUser,
  fetchAdminOverview,
  fetchAdminUsers,
  fetchAgentMonitoring,
  fetchAudioReviewTasks,
  fetchMe,
  type AgentMonitor,
  updateAdminUser,
} from "@/lib/api/admin";
import {
  deleteKnowledgeDocument,
  fetchKnowledgeDocuments,
  fetchKnowledgeStatus,
  insertKnowledgeText,
  KnowledgeDocument,
  KnowledgeQueryResult,
  KnowledgeStatus,
  queryKnowledgeBase,
  uploadKnowledgeDocument,
} from "@/lib/api/knowledgeBase";
import { InterviewAudioReviewPanel } from "./InterviewAudioReviewPanel";

type AdminSection = "overview" | "users" | "questions" | "audio" | "agents";
type AdminDashboardProps = {
  initialUser?: AuthUser | null;
  initialOverview?: AdminOverview | null;
  initialUsers?: AuthUser[];
  initialAgents?: AgentMonitor[];
  initialAudioTasks?: AudioReviewTask[];
  initialMessage?: string;
  initialForbidden?: boolean;
};

const NAV_ITEMS: Array<{ key: AdminSection; label: string; icon: typeof BarChart3 }> = [
  { key: "overview", label: "数据总览", icon: BarChart3 },
  { key: "users", label: "用户管理", icon: UsersRound },
  { key: "questions", label: "题库管理", icon: Database },
  { key: "audio", label: "录音审核", icon: FileAudio },
  { key: "agents", label: "Agent 监控", icon: Activity },
];

export function AdminDashboard({
  initialUser = null,
  initialOverview = null,
  initialUsers = [],
  initialAgents = [],
  initialAudioTasks = [],
  initialMessage = "",
  initialForbidden = false,
}: AdminDashboardProps) {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(initialUser);
  const [section, setSection] = useState<AdminSection>("overview");
  const [overview, setOverview] = useState<AdminOverview | null>(initialOverview);
  const [users, setUsers] = useState<AuthUser[]>(initialUsers);
  const [agents, setAgents] = useState<AgentMonitor[]>(initialAgents);
  const [audioTasks, setAudioTasks] = useState<AudioReviewTask[]>(initialAudioTasks);
  const [selectedAudioTaskId, setSelectedAudioTaskId] = useState(
    initialAudioTasks.find((task) => task.has_result)?.task_id || "",
  );
  const [loading, setLoading] = useState(!initialUser && !initialForbidden);
  const [message, setMessage] = useState(initialMessage);
  const [forbidden, setForbidden] = useState(initialForbidden);
  const [needsLogin, setNeedsLogin] = useState(false);

  useEffect(() => {
    if (initialUser) {
      setCurrentUser(initialUser);
      setLoading(false);
      setForbidden(initialForbidden || initialUser.role !== "admin");
      if (initialUser.role === "admin" && !initialOverview) {
        loadAdminData().catch((error) => {
          setMessage(error instanceof Error ? error.message : "后台数据加载失败，请稍后重试。");
        });
      }
      return;
    }

    const session = getAuthSession();
    if (!session) {
      setNeedsLogin(true);
      setLoading(false);
      router.replace("/login");
      return;
    }
    const activeSession = session;
    async function initializeAdmin() {
      try {
        const response = await fetchMe();
        saveAuthSession({ token: activeSession.token, user: response.user });
        setCurrentUser(response.user);
        if (response.user.role !== "admin") {
          setForbidden(true);
          return;
        }
        try {
          await loadAdminData();
        } catch (error) {
          setMessage(error instanceof Error ? error.message : "后台数据加载失败，请稍后重试。");
        }
      } catch {
        clearAuthSession();
        setNeedsLogin(true);
        router.replace("/login");
      } finally {
        setLoading(false);
      }
    }
    void initializeAdmin();
  }, [router]);

  async function loadAdminData() {
    setMessage("");
    const [overviewData, usersData, monitorData, audioData] = await Promise.all([
      fetchAdminOverview(),
      fetchAdminUsers(),
      fetchAgentMonitoring(),
      fetchAudioReviewTasks(),
    ]);
    setOverview(overviewData);
    setUsers(usersData.users);
    setAgents(monitorData.agents);
    setAudioTasks(audioData.tasks);
    setSelectedAudioTaskId((current) => current || audioData.tasks.find((task) => task.has_result)?.task_id || "");
  }

  async function handleReloadAdminData() {
    setLoading(true);
    try {
      await loadAdminData();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "后台数据刷新失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  }

  function handleSignOut() {
    clearAuthSession();
    window.location.href = "/logout";
  }

  const selectedAudioTask = useMemo(
    () => audioTasks.find((task) => task.task_id === selectedAudioTaskId),
    [audioTasks, selectedAudioTaskId],
  );

  if (loading) {
    return (
      <main className="auth-loading">
        <Loader2 className="spin-icon" size={22} />
        <span>正在加载后台...</span>
        <a className="auth-loading-link" href="/login">如果长时间停留，请点此重新登录</a>
      </main>
    );
  }

  if (needsLogin) {
    return (
      <main className="admin-forbidden">
        <ShieldCheck size={34} />
        <h1>请先登录</h1>
        <p>后台需要管理员登录态。若页面没有自动跳转，请直接进入登录页。</p>
        <a className="admin-primary" href="/login">去登录</a>
      </main>
    );
  }

  if (forbidden) {
    return (
      <main className="admin-forbidden">
        <ShieldCheck size={34} />
        <h1>需要管理员权限</h1>
        <p>当前账号只能使用面试助手工作台，无法访问题库、录音入库和后台数据。</p>
        <button type="button" className="admin-primary" onClick={() => router.replace("/")}>返回用户工作台</button>
      </main>
    );
  }

  return (
    <main className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <div><Bot size={24} /></div>
          <strong>面试助手后台</strong>
        </div>
        <nav className="admin-nav">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <button type="button" key={item.key} className={section === item.key ? "active" : ""} onClick={() => setSection(item.key)}>
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>
        <div className="admin-profile">
          <strong>{currentUser?.name}</strong>
          <span>{currentUser?.email}</span>
          <button type="button" onClick={handleSignOut}><LogOut size={15} />退出登录</button>
        </div>
      </aside>

      <section className="admin-main">
        <header className="admin-top">
          <div>
            <h1>{NAV_ITEMS.find((item) => item.key === section)?.label}</h1>
            <p>管理员处理题库、用户、录音入库和 Agent 运行状态。</p>
          </div>
          <button type="button" className="admin-secondary" onClick={() => void handleReloadAdminData()}>
            <RefreshCcw size={16} />刷新数据
          </button>
        </header>

        {message && <div className="admin-message">{message}</div>}

        {section === "overview" && overview && <OverviewSection overview={overview} />}
        {section === "users" && (
          <UsersSection
            users={users}
            currentUserId={currentUser?.id || ""}
            onMessage={setMessage}
            onReload={async () => {
              const data = await fetchAdminUsers();
              setUsers(data.users);
            }}
          />
        )}
        {section === "questions" && <QuestionBankSection />}
        {section === "audio" && (
          <AudioReviewSection
            tasks={audioTasks}
            selectedTask={selectedAudioTask}
            selectedTaskId={selectedAudioTaskId}
            onSelect={setSelectedAudioTaskId}
            onUpdated={(report) => {
              setAudioTasks((items) =>
                items.map((task) =>
                  task.task_id === report.task_id
                    ? { ...task, result: report, review_status: report.review_status, overall_score: report.summary.overall_score, qa_count: report.qa_analysis?.length || 0 }
                    : task,
                ),
              );
            }}
          />
        )}
        {section === "agents" && <AgentSection agents={agents} />}
      </section>
    </main>
  );
}

function OverviewSection({ overview }: { overview: AdminOverview }) {
  const maxRuns = Math.max(...overview.agent_counts.map((item) => item.runs), 1);
  return (
    <div className="admin-stack">
      <div className="admin-metric-grid">
        {overview.metrics.map((metric) => (
          <article className={`admin-metric ${metric.tone}`} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <p>{metric.hint}</p>
          </article>
        ))}
      </div>

      <div className="admin-two-col">
        <article className="admin-card">
          <div className="admin-card-head">
            <h2>用户数据分析</h2>
            <UsersRound size={18} />
          </div>
          <div className="admin-kv-grid">
            <span>普通用户<strong>{overview.users.regular_users}</strong></span>
            <span>管理员<strong>{overview.users.admins}</strong></span>
            <span>近 7 天新增<strong>{overview.users.new_7d}</strong></span>
            <span>停用账号<strong>{overview.users.disabled}</strong></span>
          </div>
        </article>

        <article className="admin-card">
          <div className="admin-card-head">
            <h2>题库状态</h2>
            <Database size={18} />
          </div>
          <div className="admin-kv-grid">
            <span>资料文档<strong>{overview.question_bank.documents}</strong></span>
            <span>文本分块<strong>{overview.question_bank.chunks}</strong></span>
            <span>图谱节点<strong>{overview.question_bank.graph_nodes}</strong></span>
            <span>检索服务<strong>{overview.question_bank.external_available ? "在线" : "本地"}</strong></span>
          </div>
        </article>
      </div>

      <article className="admin-card">
        <div className="admin-card-head">
          <h2>Agent 产物分布</h2>
          <Activity size={18} />
        </div>
        <div className="admin-bars">
          {overview.agent_counts.map((item) => (
            <div key={item.key}>
              <span>{item.label}</span>
              <div><i style={{ width: `${Math.max(6, (item.runs / maxRuns) * 100)}%` }} /></div>
              <strong>{item.runs}</strong>
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}

function UsersSection({
  users,
  currentUserId,
  onMessage,
  onReload,
}: {
  users: AuthUser[];
  currentUserId: string;
  onMessage: (message: string) => void;
  onReload: () => Promise<void>;
}) {
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "user" as "user" | "admin" });
  const [saving, setSaving] = useState(false);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    onMessage("");
    try {
      await createAdminUser(form);
      setForm({ name: "", email: "", password: "", role: "user" });
      await onReload();
      onMessage("用户已创建。");
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "用户创建失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdate(userId: string, field: "role" | "status", value: string) {
    setSaving(true);
    onMessage("");
    try {
      await updateAdminUser(userId, { [field]: value });
      await onReload();
      onMessage("用户信息已更新。");
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "用户更新失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="admin-stack">
      <article className="admin-card">
        <div className="admin-card-head">
          <h2>创建用户</h2>
          <UserPlus size={18} />
        </div>
        <form className="admin-inline-form" onSubmit={handleCreate}>
          <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="姓名" />
          <input value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="邮箱" type="email" />
          <input value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} placeholder="初始密码" type="password" />
          <select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value as "user" | "admin" })}>
            <option value="user">普通用户</option>
            <option value="admin">管理员</option>
          </select>
          <button type="submit" className="admin-primary" disabled={saving}>创建</button>
        </form>
      </article>

      <article className="admin-card">
        <div className="admin-card-head">
          <h2>用户列表</h2>
          <span>{users.length} 人</span>
        </div>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>用户</th>
                <th>角色</th>
                <th>状态</th>
                <th>最近登录</th>
                <th>注册时间</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>
                    <strong>{user.name}</strong>
                    <span>{user.email}</span>
                  </td>
                  <td>
                    <select value={user.role} disabled={saving} onChange={(event) => void handleUpdate(user.id, "role", event.target.value)}>
                      <option value="user">普通用户</option>
                      <option value="admin">管理员</option>
                    </select>
                  </td>
                  <td>
                    <select value={user.status} disabled={saving || user.id === currentUserId} onChange={(event) => void handleUpdate(user.id, "status", event.target.value)}>
                      <option value="active">启用</option>
                      <option value="disabled">停用</option>
                    </select>
                  </td>
                  <td>{formatDate(user.last_login_at)}</td>
                  <td>{formatDate(user.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </div>
  );
}

function QuestionBankSection() {
  const [status, setStatus] = useState<KnowledgeStatus | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [query, setQuery] = useState("Java 后端 Redis 面试题");
  const [queryResult, setQueryResult] = useState<KnowledgeQueryResult | null>(null);
  const [textTitle, setTextTitle] = useState("");
  const [textContent, setTextContent] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setLoading(true);
    setMessage("");
    try {
      const [statusData, documentsData] = await Promise.all([fetchKnowledgeStatus(), fetchKnowledgeDocuments()]);
      setStatus(statusData);
      setDocuments(documentsData.documents);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "题库读取失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setMessage("");
    try {
      await uploadKnowledgeDocument(file);
      setMessage("资料已上传并写入题库。");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "资料上传失败");
    } finally {
      setLoading(false);
      event.target.value = "";
    }
  }

  async function handleInsertText() {
    if (!textContent.trim()) {
      setMessage("请先粘贴题库文本。");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      await insertKnowledgeText({ title: textTitle || "管理员录入题库.md", text: textContent });
      setTextTitle("");
      setTextContent("");
      setMessage("题库文本已写入。");
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "文本写入失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch() {
    setLoading(true);
    setMessage("");
    try {
      setQueryResult(await queryKnowledgeBase({ query, top_k: 6 }));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "题库检索失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(documentId: string) {
    setLoading(true);
    setMessage("");
    try {
      await deleteKnowledgeDocument(documentId);
      setDocuments((items) => items.filter((item) => item.id !== documentId));
      setMessage("资料已删除。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "资料删除失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="admin-stack">
      {message && <div className="admin-message local">{message}</div>}
      <div className="admin-metric-grid compact">
        <article className="admin-metric blue"><span>文档</span><strong>{status?.local_index.document_count ?? 0}</strong><p>面试题、宝典与内部资料</p></article>
        <article className="admin-metric green"><span>分块</span><strong>{status?.local_index.chunk_count ?? 0}</strong><p>用于 RAG 检索</p></article>
        <article className="admin-metric orange"><span>图谱节点</span><strong>{status?.graph.node_count ?? 0}</strong><p>概念和题型关系</p></article>
        <article className="admin-metric gray"><span>检索服务</span><strong>{status?.external_retrieval.available ? "在线" : "本地"}</strong><p>{status?.external_retrieval.status || "unknown"}</p></article>
      </div>

      <div className="admin-two-col">
        <article className="admin-card">
          <div className="admin-card-head">
            <h2>上传或录入题库</h2>
            <Upload size={18} />
          </div>
          <div className="admin-form-stack">
            <button type="button" className="admin-secondary" onClick={() => fileRef.current?.click()} disabled={loading}>
              <Upload size={16} />上传 PDF / DOCX / TXT / MD
            </button>
            <input ref={fileRef} hidden type="file" accept=".pdf,.docx,.txt,.md,.markdown,.json,.csv" onChange={handleUpload} />
            <input value={textTitle} onChange={(event) => setTextTitle(event.target.value)} placeholder="文本标题，例如 Java 高频题.md" />
            <textarea value={textContent} onChange={(event) => setTextContent(event.target.value)} placeholder="粘贴题库内容、面试题和标准答案..." />
            <button type="button" className="admin-primary" onClick={handleInsertText} disabled={loading}>写入题库</button>
          </div>
        </article>

        <article className="admin-card">
          <div className="admin-card-head">
            <h2>题库检索测试</h2>
            <Search size={18} />
          </div>
          <div className="admin-search-row">
            <input value={query} onChange={(event) => setQuery(event.target.value)} />
            <button type="button" className="admin-primary" onClick={handleSearch} disabled={loading}><Send size={16} />检索</button>
          </div>
          {queryResult && (
            <div className="admin-result-box">
              <strong>{queryResult.available ? "外部检索结果" : "本地题库结果"}</strong>
              <p>{queryResult.answer || "暂无答案摘要。"}</p>
              <span>{queryResult.references.length} 条引用</span>
            </div>
          )}
        </article>
      </div>

      <article className="admin-card">
        <div className="admin-card-head">
          <h2>题库资料</h2>
          <button type="button" className="admin-secondary" onClick={() => void refresh()} disabled={loading}><RefreshCcw size={16} />刷新</button>
        </div>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>资料</th>
                <th>状态</th>
                <th>分块</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((document) => (
                <tr key={document.id}>
                  <td><strong>{document.filename}</strong><span>{document.content_summary || document.file_path}</span></td>
                  <td>{document.status}</td>
                  <td>{document.chunks_count}</td>
                  <td>{formatDate(document.updated_at || document.created_at)}</td>
                  <td>
                    <button type="button" className="admin-danger" onClick={() => void handleDelete(document.id)} disabled={loading}>
                      <Trash2 size={15} />删除
                    </button>
                  </td>
                </tr>
              ))}
              {!documents.length && <tr><td colSpan={5}>暂无题库资料。</td></tr>}
            </tbody>
          </table>
        </div>
      </article>
    </div>
  );
}

function AudioReviewSection({
  tasks,
  selectedTask,
  selectedTaskId,
  onSelect,
  onUpdated,
}: {
  tasks: AudioReviewTask[];
  selectedTask?: AudioReviewTask;
  selectedTaskId: string;
  onSelect: (taskId: string) => void;
  onUpdated: Parameters<typeof InterviewAudioReviewPanel>[0]["onUpdated"];
}) {
  return (
    <div className="admin-audio-layout">
      <article className="admin-card audio-task-list">
        <div className="admin-card-head">
          <h2>录音任务</h2>
          <span>{tasks.length} 个</span>
        </div>
        <div className="admin-task-list">
          {tasks.map((task) => (
            <button type="button" key={task.task_id} className={selectedTaskId === task.task_id ? "active" : ""} onClick={() => onSelect(task.task_id)}>
              <strong>{task.audio_filename || task.task_id}</strong>
              <span>{task.review_status || task.status} · {task.qa_count} 题 · {formatDate(task.updated_at)}</span>
            </button>
          ))}
          {!tasks.length && <div className="admin-empty">暂无录音分析任务。</div>}
        </div>
      </article>

      <div className="admin-audio-review">
        {selectedTask?.result ? (
          <InterviewAudioReviewPanel report={selectedTask.result} canManage onUpdated={onUpdated} />
        ) : (
          <article className="admin-card admin-empty large">
            <FileAudio size={28} />
            <strong>请选择一个已完成分析的录音任务</strong>
            <p>用户端生成分析结果后，管理员在这里审核题目和标准答案，并决定是否写入题库。</p>
          </article>
        )}
      </div>
    </div>
  );
}

function AgentSection({ agents }: { agents: AgentMonitor[] }) {
  return (
    <article className="admin-card">
      <div className="admin-card-head">
        <h2>Agent 效果监控</h2>
        <Activity size={18} />
      </div>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Agent</th>
              <th>运行次数</th>
              <th>完成率</th>
              <th>状态</th>
              <th>说明</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((agent) => (
              <tr key={agent.key}>
                <td><strong>{agent.name}</strong><span>{agent.key}</span></td>
                <td>{agent.runs}</td>
                <td>{agent.success_rate == null ? "待接入" : `${agent.success_rate}%`}</td>
                <td>
                  <span className={`admin-status ${agent.status}`}>
                    <CheckCircle2 size={14} />{agent.status === "attention" ? "需关注" : "正常"}
                  </span>
                </td>
                <td>{agent.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "未记录";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}
