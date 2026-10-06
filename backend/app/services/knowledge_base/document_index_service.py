from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from .config import KnowledgeBaseConfig, knowledge_base_config


@dataclass
class LocalSearchHit:
    chunk_id: str
    doc_id: str
    file_path: str
    snippet: str
    score: float


class DocumentIndexService:
    """Local document/index facade for the embedded interview knowledge base."""

    def __init__(self, config: KnowledgeBaseConfig | None = None) -> None:
        self.config = config or knowledge_base_config
        self.working_dir = self.config.working_dir
        self.input_dir = self.config.input_dir
        self.doc_status_path = self.working_dir / "kv_store_doc_status.json"
        self.full_docs_path = self.working_dir / "kv_store_full_docs.json"
        self.text_chunks_path = self.working_dir / "kv_store_text_chunks.json"

    def list_documents(self) -> list[dict[str, Any]]:
        statuses = self._read_json(self.doc_status_path, {})
        full_docs = self._read_json(self.full_docs_path, {})
        documents: list[dict[str, Any]] = []
        seen: set[str] = set()

        if isinstance(statuses, dict):
            for doc_id, item in statuses.items():
                if not isinstance(item, dict):
                    continue
                seen.add(str(doc_id))
                documents.append(self._normalize_doc(str(doc_id), item, full_docs.get(doc_id) if isinstance(full_docs, dict) else None))

        if isinstance(full_docs, dict):
            for doc_id, item in full_docs.items():
                if str(doc_id) in seen:
                    continue
                documents.append(self._normalize_doc(str(doc_id), {}, item))

        return sorted(documents, key=lambda item: str(item.get("updated_at") or ""), reverse=True)

    async def upload_document(self, upload: UploadFile) -> dict[str, Any]:
        safe_name = self._safe_filename(upload.filename or "knowledge.txt")
        target = self.input_dir / safe_name
        with target.open("wb") as file_obj:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                file_obj.write(chunk)
        text = self._extract_text(target)
        if not text.strip():
            raise ValueError("文档内容为空，无法写入知识库。")
        document = self.insert_text(title=safe_name, text=text, source_path=safe_name)
        document["saved_path"] = str(target)
        return document

    def insert_text(self, *, title: str | None, text: str, source_path: str | None = None) -> dict[str, Any]:
        content = (text or "").strip()
        if not content:
            raise ValueError("文档内容为空，无法写入知识库。")

        now = datetime.now(timezone.utc).isoformat()
        title = self._safe_filename(title or f"interview-kb-{now}.md")
        doc_id = "doc-" + hashlib.md5(f"{title}:{content[:1000]}".encode("utf-8")).hexdigest()
        chunks = self._split_text(content)
        chunk_ids = [self._chunk_id(doc_id, index, chunk) for index, chunk in enumerate(chunks)]

        doc_status = self._read_json(self.doc_status_path, {})
        full_docs = self._read_json(self.full_docs_path, {})
        text_chunks = self._read_json(self.text_chunks_path, {})
        if not isinstance(doc_status, dict):
            doc_status = {}
        if not isinstance(full_docs, dict):
            full_docs = {}
        if not isinstance(text_chunks, dict):
            text_chunks = {}

        doc_status[doc_id] = {
            "status": "processed",
            "chunks_count": len(chunks),
            "chunks_list": chunk_ids,
            "content_summary": content[:600],
            "content_length": len(content),
            "created_at": now,
            "updated_at": now,
            "file_path": source_path or title,
            "metadata": {"source": "internal_interview_knowledge_base"},
        }
        full_docs[doc_id] = {
            "content": content,
            "file_path": source_path or title,
            "title": title,
            "_id": doc_id,
        }

        for index, chunk in enumerate(chunks):
            chunk_id = chunk_ids[index]
            text_chunks[chunk_id] = {
                "tokens": len(chunk),
                "content": chunk,
                "chunk_order_index": index,
                "full_doc_id": doc_id,
                "file_path": source_path or title,
                "create_time": int(datetime.now(timezone.utc).timestamp()),
                "update_time": int(datetime.now(timezone.utc).timestamp()),
                "_id": chunk_id,
            }

        self._write_json(self.doc_status_path, doc_status)
        self._write_json(self.full_docs_path, full_docs)
        self._write_json(self.text_chunks_path, text_chunks)
        return self._normalize_doc(doc_id, doc_status[doc_id], full_docs[doc_id])

    def delete_document(self, document_id: str) -> bool:
        doc_id = (document_id or "").strip()
        if not doc_id:
            return False
        doc_status = self._read_json(self.doc_status_path, {})
        full_docs = self._read_json(self.full_docs_path, {})
        text_chunks = self._read_json(self.text_chunks_path, {})
        changed = False

        if isinstance(doc_status, dict) and doc_id in doc_status:
            doc_status.pop(doc_id, None)
            changed = True
        if isinstance(full_docs, dict) and doc_id in full_docs:
            full_docs.pop(doc_id, None)
            changed = True
        if isinstance(text_chunks, dict):
            stale = [chunk_id for chunk_id, chunk in text_chunks.items() if isinstance(chunk, dict) and chunk.get("full_doc_id") == doc_id]
            for chunk_id in stale:
                text_chunks.pop(chunk_id, None)
                changed = True

        if changed:
            self._write_json(self.doc_status_path, doc_status if isinstance(doc_status, dict) else {})
            self._write_json(self.full_docs_path, full_docs if isinstance(full_docs, dict) else {})
            self._write_json(self.text_chunks_path, text_chunks if isinstance(text_chunks, dict) else {})
        return changed

    def search(self, query: str, *, top_k: int | None = None) -> list[LocalSearchHit]:
        q = (query or "").strip()
        if not q:
            return []
        chunks = self._read_json(self.text_chunks_path, {})
        if not isinstance(chunks, dict):
            return []
        terms = self._query_terms(q)
        limit = top_k or self.config.top_k
        hits: list[LocalSearchHit] = []
        for chunk_id, chunk in chunks.items():
            if not isinstance(chunk, dict):
                continue
            content = str(chunk.get("content") or "")
            score = self._score(content, terms, q)
            if score <= 0:
                continue
            hits.append(
                LocalSearchHit(
                    chunk_id=str(chunk.get("_id") or chunk_id),
                    doc_id=str(chunk.get("full_doc_id") or ""),
                    file_path=str(chunk.get("file_path") or "面试知识库文档"),
                    snippet=self._snippet(content, terms),
                    score=score,
                )
            )
        return sorted(hits, key=lambda item: item.score, reverse=True)[:limit]

    def status(self) -> dict[str, Any]:
        docs = self.list_documents()
        chunks = self._read_json(self.text_chunks_path, {})
        chunk_count = len(chunks) if isinstance(chunks, dict) else 0
        processed = sum(1 for doc in docs if doc.get("status") == "processed")
        return {
            "document_count": len(docs),
            "processed_document_count": processed,
            "chunk_count": chunk_count,
            "input_dir": str(self.input_dir),
            "working_dir": str(self.working_dir),
        }

    def _normalize_doc(self, doc_id: str, status: dict[str, Any], full_doc: Any) -> dict[str, Any]:
        content = ""
        title = ""
        if isinstance(full_doc, dict):
            content = str(full_doc.get("content") or "")
            title = str(full_doc.get("title") or "")
        elif isinstance(full_doc, str):
            content = full_doc
        file_path = str(status.get("file_path") or title or doc_id)
        return {
            "id": doc_id,
            "filename": Path(file_path).name,
            "file_path": file_path,
            "status": str(status.get("status") or "processed"),
            "chunks_count": int(status.get("chunks_count") or 0),
            "content_length": int(status.get("content_length") or len(content)),
            "content_summary": str(status.get("content_summary") or content[:260]),
            "created_at": str(status.get("created_at") or ""),
            "updated_at": str(status.get("updated_at") or status.get("created_at") or ""),
        }

    def _extract_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md", ".markdown", ".json", ".csv"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf":
            try:
                import fitz  # type: ignore

                doc = fitz.open(str(path))
                return "\n".join(page.get_text("text") for page in doc)
            except Exception:
                return ""
        if suffix == ".docx":
            try:
                import docx  # type: ignore

                document = docx.Document(str(path))
                return "\n".join(paragraph.text for paragraph in document.paragraphs)
            except Exception:
                return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def _split_text(self, text: str) -> list[str]:
        size = max(300, self.config.chunk_size)
        overlap = min(max(0, self.config.chunk_overlap_size), size // 2)
        cleaned = re.sub(r"\n{3,}", "\n\n", text.strip())
        chunks: list[str] = []
        start = 0
        while start < len(cleaned):
            end = min(len(cleaned), start + size)
            chunk = cleaned[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(cleaned):
                break
            start = max(end - overlap, start + 1)
        return chunks or [cleaned]

    def _chunk_id(self, doc_id: str, index: int, chunk: str) -> str:
        digest = hashlib.md5(f"{doc_id}:{index}:{chunk[:160]}".encode("utf-8")).hexdigest()
        return f"chunk-{digest}"

    def _query_terms(self, query: str) -> list[str]:
        terms = re.findall(r"[A-Za-z0-9_+#.-]+|[\u4e00-\u9fff]{2,}", query.lower())
        if not terms:
            return [query.lower()]
        # Keep long Chinese queries useful by adding short phrase windows.
        extra: list[str] = []
        for term in terms:
            if re.fullmatch(r"[\u4e00-\u9fff]{5,}", term):
                extra.extend(term[index : index + 4] for index in range(0, len(term) - 3, 2))
        return list(dict.fromkeys([*terms, *extra]))

    def _score(self, content: str, terms: list[str], query: str) -> float:
        normalized = content.lower()
        score = 0.0
        for term in terms:
            if term and term in normalized:
                score += normalized.count(term) * (2.0 if len(term) > 3 else 1.0)
        if query.lower() in normalized:
            score += 8.0
        return score

    def _snippet(self, content: str, terms: list[str]) -> str:
        index = -1
        lower = content.lower()
        for term in terms:
            index = lower.find(term)
            if index >= 0:
                break
        if index < 0:
            return content[:420].strip()
        start = max(0, index - 160)
        end = min(len(content), index + 360)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(content) else ""
        return f"{prefix}{content[start:end].strip()}{suffix}"

    def _safe_filename(self, filename: str) -> str:
        name = Path(filename).name.strip() or "knowledge.txt"
        return re.sub(r"[^\w\u4e00-\u9fff.\-()（） ]+", "_", name)

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            backup = path.with_suffix(path.suffix + ".broken")
            try:
                shutil.copyfile(path, backup)
            except OSError:
                pass
            return default

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


document_index_service = DocumentIndexService()
