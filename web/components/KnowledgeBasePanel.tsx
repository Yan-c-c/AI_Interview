"use client";

import type { CSSProperties } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  BookOpen,
  Database,
  FileText,
  GitGraph,
  Layers3,
  Plus,
  RefreshCcw,
  Search,
  Send,
  Trash2,
  Upload,
  type LucideIcon,
} from "lucide-react";
import {
  deleteKnowledgeDocument,
  fetchKnowledgeDocuments,
  fetchKnowledgeGraph,
  fetchKnowledgeGraphLabels,
  fetchKnowledgeStatus,
  insertKnowledgeText,
  KnowledgeDocument,
  KnowledgeGraphData,
  KnowledgeGraphLabel,
  KnowledgeQueryResult,
  KnowledgeStatus,
  queryKnowledgeBase,
  uploadKnowledgeDocument,
} from "@/lib/api/knowledgeBase";

type KnowledgeTab = "overview" | "documents" | "search" | "graph";

const TABS: Array<{ key: KnowledgeTab; label: string }> = [
  { key: "overview", label: "总览" },
  { key: "documents", label: "文档管理" },
  { key: "search", label: "知识检索" },
  { key: "graph", label: "知识图谱" },
];

export function KnowledgeBasePanel() {
  const [activeTab, setActiveTab] = useState<KnowledgeTab>("overview");
  const [status, setStatus] = useState<KnowledgeStatus | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [labels, setLabels] = useState<KnowledgeGraphLabel[]>([]);
  const [graph, setGraph] = useState<KnowledgeGraphData | null>(null);
  const [query, setQuery] = useState("Java Spring Boot Redis 项目 面试题");
  const [queryResult, setQueryResult] = useState<KnowledgeQueryResult | null>(null);
  const [graphQuery, setGraphQuery] = useState("");
  const [textTitle, setTextTitle] = useState("");
  const [textContent, setTextContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const headline = useMemo(() => {
    if (!status) return "正在读取面试知识库状态";
    const docs = status.local_index.document_count;
    const nodes = status.graph.node_count;
    return `已接入 ${docs} 份资料，知识图谱包含 ${nodes} 个节点`;
  }, [status]);

  useEffect(() => {
    void refreshAll();
  }, []);

  async function refreshAll() {
    setLoading(true);
    setMessage("");
    try {
      const [statusData, documentsData, labelsData, graphData] = await Promise.all([
        fetchKnowledgeStatus(),
        fetchKnowledgeDocuments(),
        fetchKnowledgeGraphLabels({ limit: 24 }),
        fetchKnowledgeGraph({ max_depth: 2, max_nodes: 80 }),
      ]);
      setStatus(statusData);
      setDocuments(documentsData.documents);
      setLabels(labelsData.labels);
      setGraph(graphData.graph);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "知识库读取失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(file?: File) {
    if (!file) return;
    setLoading(true);
    setMessage("");
    try {
      await uploadKnowledgeDocument(file);
      setMessage("文档已写入面试知识库。");
      await refreshAll();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "文档上传失败");
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleInsertText() {
    if (!textContent.trim()) {
      setMessage("请先输入要写入知识库的题库文本。");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      await insertKnowledgeText({ title: textTitle.trim() || "手动录入面试题.md", text: textContent });
      setTextTitle("");
      setTextContent("");
      setMessage("文本内容已写入面试知识库。");
      await refreshAll();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "文本写入失败");
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
      setMessage("文档已从面试知识库中移除。");
      void refreshAll();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "文档删除失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch() {
    if (!query.trim()) {
      setMessage("请输入检索关键词。");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const result = await queryKnowledgeBase({ query, top_k: 8 });
      setQueryResult(result);
      setActiveTab("search");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "知识检索失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleGraphSearch(label?: string) {
    setLoading(true);
    setMessage("");
    try {
      const keyword = label ?? graphQuery.trim();
      const [labelsData, graphData] = await Promise.all([
        fetchKnowledgeGraphLabels({ q: keyword || undefined, limit: 30 }),
        fetchKnowledgeGraph({ label: keyword || undefined, max_depth: 2, max_nodes: 90 }),
      ]);
      setLabels(labelsData.labels);
      setGraph(graphData.graph);
      setActiveTab("graph");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "知识图谱读取失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="knowledge-workspace">
      <header className="kb-hero">
        <div>
          <div className="kb-eyebrow"><Database size={16} /> 面试知识库</div>
          <h2>题库管理与知识检索</h2>
          <p>{headline}</p>
        </div>
        <div className="kb-hero-actions">
          <button type="button" className="outline-button" onClick={refreshAll} disabled={loading}>
            <RefreshCcw size={16} />刷新
          </button>
          <button type="button" className="primary-button" onClick={() => fileInputRef.current?.click()} disabled={loading}>
            <Upload size={16} />上传资料
          </button>
          <input
            ref={fileInputRef}
            type="file"
            hidden
            accept=".pdf,.docx,.txt,.md,.markdown,.json,.csv"
            onChange={(event) => void handleUpload(event.target.files?.[0])}
          />
        </div>
      </header>

      <nav className="kb-tabs" aria-label="知识库导航">
        {TABS.map((tab) => (
          <button
            type="button"
            key={tab.key}
            className={activeTab === tab.key ? "active" : ""}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {message && <div className="kb-toast">{message}</div>}

      {activeTab === "overview" && (
        <div className="kb-overview">
          <div className="kb-metric-grid">
            <MetricCard icon={BookOpen} label="资料文档" value={status?.local_index.document_count ?? 0} hint="真实面试题、面试宝典与内部资料" />
            <MetricCard icon={Layers3} label="文本分块" value={status?.local_index.chunk_count ?? 0} hint="用于 RAG 检索的知识片段" />
            <MetricCard icon={GitGraph} label="图谱节点" value={status?.graph.node_count ?? 0} hint="技能、项目、概念和题型关系" />
            <MetricCard icon={Activity} label="检索服务" value={status?.external_retrieval.available ? "在线" : "本地"} hint={status?.external_retrieval.available ? "外部检索服务可用" : "使用内嵌索引兜底检索"} />
          </div>

          <div className="kb-main-grid">
            <article className="kb-card kb-search-card">
              <div className="kb-card-head">
                <div>
                  <h3>快速检索面试题库</h3>
                  <p>用于验证当前知识库是否能支撑模拟面试 Agent 的题目生成。</p>
                </div>
                <Search size={20} />
              </div>
              <div className="kb-search-row">
                <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="输入岗位、技能、项目关键词" />
                <button type="button" className="primary-button" onClick={handleSearch} disabled={loading}>
                  <Send size={16} />检索
                </button>
              </div>
              <div className="kb-chip-row">
                {["Java 后端 Redis 面试", "大模型 RAG 项目", "Spring Boot 权限系统", "项目深挖题"].map((item) => (
                  <button type="button" key={item} onClick={() => setQuery(item)}>{item}</button>
                ))}
              </div>
            </article>

            <article className="kb-card">
              <div className="kb-card-head">
                <div>
                  <h3>知识图谱热点</h3>
                  <p>点击节点可查看相关概念与题库资料关系。</p>
                </div>
                <GitGraph size={20} />
              </div>
              <div className="kb-label-list">
                {labels.slice(0, 12).map((item) => (
                  <button type="button" key={item.label} onClick={() => void handleGraphSearch(item.label)}>
                    <span>{item.label}</span>
                    <small>{item.degree}</small>
                  </button>
                ))}
              </div>
            </article>
          </div>
        </div>
      )}

      {activeTab === "documents" && (
        <div className="kb-documents-grid">
          <article className="kb-card kb-text-insert">
            <div className="kb-card-head">
              <div>
                <h3>录入题库文本</h3>
                <p>可粘贴真实面试题、公司面经、复习资料，写入后会作为 Agent 检索线索。</p>
              </div>
              <Plus size={20} />
            </div>
            <input value={textTitle} onChange={(event) => setTextTitle(event.target.value)} placeholder="标题，例如 Java 高频面试题.md" />
            <textarea value={textContent} onChange={(event) => setTextContent(event.target.value)} placeholder="粘贴题库内容或面试宝典片段..." />
            <button type="button" className="primary-button" onClick={handleInsertText} disabled={loading}>
              写入知识库
            </button>
          </article>

          <article className="kb-card kb-document-list">
            <div className="kb-card-head">
              <div>
                <h3>资料列表</h3>
                <p>当前系统内嵌知识库的文档与索引状态。</p>
              </div>
              <FileText size={20} />
            </div>
            <div className="kb-doc-list">
              {documents.map((doc) => (
                <div className="kb-doc-row" key={doc.id}>
                  <div className="kb-doc-icon"><FileText size={18} /></div>
                  <div>
                    <strong>{doc.filename}</strong>
                    <p>{doc.chunks_count} 个片段 · {doc.content_length} 字 · {doc.status}</p>
                    <span>{doc.content_summary}</span>
                  </div>
                  <button type="button" aria-label="删除文档" onClick={() => void handleDelete(doc.id)} disabled={loading}>
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
              {documents.length === 0 && <div className="kb-empty">暂无知识库资料，先上传一份面试题 PDF 或粘贴题库文本。</div>}
            </div>
          </article>
        </div>
      )}

      {activeTab === "search" && (
        <div className="kb-search-layout">
          <article className="kb-card">
            <div className="kb-card-head">
              <div>
                <h3>知识库检索</h3>
                <p>检索真实面试题库和面试宝典，结果会作为模拟面试 Agent 的引用依据。</p>
              </div>
              <Search size={20} />
            </div>
            <textarea className="kb-query-box" value={query} onChange={(event) => setQuery(event.target.value)} />
            <button type="button" className="primary-button" onClick={handleSearch} disabled={loading}>
              开始检索
            </button>
          </article>

          <article className="kb-card kb-result-card">
            <div className="kb-card-head">
              <div>
                <h3>检索结果</h3>
                <p>{queryResult ? `来源：${queryResult.source === "external_service" ? "检索服务" : "内嵌索引"}` : "等待检索"}</p>
              </div>
              <Database size={20} />
            </div>
            {queryResult ? (
              <>
                <div className="kb-answer">{queryResult.answer || "未生成摘要，以下为命中的知识片段。"}</div>
                <div className="kb-reference-list">
                  {queryResult.references.map((ref) => (
                    <div className="kb-reference" key={ref.reference_id}>
                      <strong>{ref.file_path}</strong>
                      <p>{ref.content.join("\n")}</p>
                    </div>
                  ))}
                  {queryResult.references.length === 0 && <div className="kb-empty">没有命中相关知识片段。</div>}
                </div>
              </>
            ) : (
              <div className="kb-empty">输入技能、岗位或项目关键词后开始检索。</div>
            )}
          </article>
        </div>
      )}

      {activeTab === "graph" && (
        <div className="kb-graph-layout">
          <article className="kb-card kb-graph-panel">
            <div className="kb-card-head">
              <div>
                <h3>知识图谱管理</h3>
                <p>查看技能、项目、题型和知识点之间的关联。</p>
              </div>
              <GitGraph size={20} />
            </div>
            <div className="kb-search-row">
              <input value={graphQuery} onChange={(event) => setGraphQuery(event.target.value)} placeholder="搜索图谱节点，例如 Redis、RAG、Spring" />
              <button type="button" className="outline-button" onClick={() => void handleGraphSearch()} disabled={loading}>
                查看图谱
              </button>
            </div>
            <GraphCanvas graph={graph} onPick={(label) => void handleGraphSearch(label)} />
          </article>

          <article className="kb-card">
            <div className="kb-card-head">
              <div>
                <h3>节点列表</h3>
                <p>按连接度排序，适合作为题库检索入口。</p>
              </div>
              <BookOpen size={20} />
            </div>
            <div className="kb-label-list vertical">
              {labels.map((item) => (
                <button type="button" key={item.label} onClick={() => void handleGraphSearch(item.label)}>
                  <span>{item.label}</span>
                  <small>{item.entity_type || "concept"} · {item.degree}</small>
                </button>
              ))}
            </div>
          </article>
        </div>
      )}
    </section>
  );
}

function MetricCard({ icon: Icon, label, value, hint }: { icon: LucideIcon; label: string; value: string | number; hint: string }) {
  return (
    <article className="kb-metric-card">
      <div><Icon size={20} /></div>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{hint}</p>
    </article>
  );
}

function GraphCanvas({ graph, onPick }: { graph: KnowledgeGraphData | null; onPick: (label: string) => void }) {
  if (!graph || graph.nodes.length === 0) {
    return <div className="kb-graph-canvas empty">暂无图谱数据</div>;
  }
  const nodes = graph.nodes.slice(0, 18);
  const centerIndex = nodes.findIndex((node) => node.root);
  const positions = nodes.map((node, index) => {
    if (index === centerIndex || (centerIndex < 0 && index === 0)) {
      return { left: "50%", top: "50%", transform: "translate(-50%, -50%)" };
    }
    const angle = (Math.PI * 2 * index) / Math.max(nodes.length - 1, 1);
    const radius = 38;
    return {
      left: `${50 + Math.cos(angle) * radius}%`,
      top: `${50 + Math.sin(angle) * radius}%`,
      transform: "translate(-50%, -50%)",
    };
  });

  return (
    <div className="kb-graph-canvas">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {graph.edges.slice(0, 30).map((edge) => {
          const sourceIndex = nodes.findIndex((node) => node.id === edge.source);
          const targetIndex = nodes.findIndex((node) => node.id === edge.target);
          if (sourceIndex < 0 || targetIndex < 0) return null;
          const source = positions[sourceIndex];
          const target = positions[targetIndex];
          return (
            <line
              key={edge.id}
              x1={parseFloat(source.left)}
              y1={parseFloat(source.top)}
              x2={parseFloat(target.left)}
              y2={parseFloat(target.top)}
            />
          );
        })}
      </svg>
      {nodes.map((node, index) => {
        const style = positions[index] as CSSProperties;
        return (
          <button
            type="button"
            key={node.id}
            className={node.root ? "root" : ""}
            style={style}
            onClick={() => onPick(node.label)}
            title={node.description || node.label}
          >
            {node.label}
          </button>
        );
      })}
    </div>
  );
}
