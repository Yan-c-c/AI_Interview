from __future__ import annotations

import json
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.knowledge_base import knowledge_base_service


class AudioReviewService:
    def __init__(self) -> None:
        self.base_dir = Path(__file__).resolve().parents[2] / "data" / "audio_reviews"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_path = self.base_dir / "audio_analysis_tasks.json"
        self.logs_path = self.base_dir / "audio_review_logs.json"

    def create_task(
        self,
        *,
        audio_filename: str,
        audio_file_id: str | None = None,
        audio_url: str | None = None,
        audio_sha256: str | None = None,
    ) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            "status": "created",
            "review_status": "pending_analysis",
            "audio_filename": audio_filename,
            "audio_file_id": audio_file_id,
            "audio_url": audio_url,
            "audio_sha256": audio_sha256,
            "created_at": self._now(),
            "updated_at": self._now(),
            "result": None,
            "error": None,
        }
        self.save_task(task)
        return task

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        return self._load_tasks().get(task_id)

    def find_reusable_task(
        self,
        *,
        audio_file_id: str | None = None,
        audio_url: str | None = None,
        audio_sha256: str | None = None,
    ) -> dict[str, Any] | None:
        if not audio_file_id and not audio_url and not audio_sha256:
            return None
        tasks = sorted(self._load_tasks().values(), key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        for task in tasks:
            if not self._matches_audio(task, audio_file_id=audio_file_id, audio_url=audio_url, audio_sha256=audio_sha256):
                continue
            if task.get("status") in {"created", "transcribing", "transcribed"} and (task.get("baidu_task_id") or isinstance(task.get("result"), dict)):
                return task
            if task.get("status") in {"completed", "reviewed"} and isinstance(task.get("result"), dict):
                result = task["result"]
                transcript = result.get("transcript") if isinstance(result.get("transcript"), dict) else {}
                if transcript.get("raw_text") or result.get("qa_analysis"):
                    return task
        return None

    def save_task(self, task: dict[str, Any]) -> None:
        tasks = self._load_tasks()
        task["updated_at"] = self._now()
        tasks[task["task_id"]] = task
        self.tasks_path.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")

    def update_result(self, task_id: str, result: dict[str, Any], *, status: str = "completed") -> dict[str, Any]:
        task = self.get_task(task_id) or {"task_id": task_id, "created_at": self._now()}
        task["status"] = status
        task["review_status"] = result.get("review_status") or "pending_review"
        task["result"] = result
        task["error"] = None
        self.save_task(task)
        return task

    def fail_task(self, task_id: str, error: str) -> dict[str, Any]:
        task = self.get_task(task_id) or {"task_id": task_id, "created_at": self._now()}
        task["status"] = "failed"
        task["review_status"] = "analysis_failed"
        task["error"] = error
        self.save_task(task)
        return task

    async def approve(self, task_id: str, *, reviewer: str = "讲师", updates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        task = self.get_task(task_id)
        if not task or not isinstance(task.get("result"), dict):
            raise ValueError("未找到可审核的录音分析任务。")
        result = task["result"]
        qa_analysis = list(result.get("qa_analysis") or [])
        qa_analysis = self._apply_updates(qa_analysis, updates or [])
        if not any(str(item.get("question") or "").strip() and str(item.get("standard_answer") or "").strip() for item in qa_analysis):
            raise ValueError("当前分析结果没有可入库的题目和标准答案，请等待转写完成或先补充审核内容。")
        ingest_text = self._format_ingest_text(qa_analysis, reviewer=reviewer)
        document = await knowledge_base_service.insert_text(
            title=f"面试录音审核收录-{task_id}.md",
            text=ingest_text,
        )
        result["qa_analysis"] = qa_analysis
        result["review_status"] = "approved"
        result.setdefault("metadata", {})["knowledge_base_document_id"] = document.get("id")
        result["metadata"]["knowledge_base_track_id"] = document.get("external_ingest", {}).get("track_id") or document.get("id")
        task["status"] = "reviewed"
        task["review_status"] = "approved"
        task["result"] = result
        self.save_task(task)
        log = self._append_log(task_id, reviewer=reviewer, action="approve", detail={"document": document})
        return {"success": True, "task": task, "knowledge_base_document": document, "review_log": log}

    def reject(self, task_id: str, *, reviewer: str = "讲师", reason: str = "") -> dict[str, Any]:
        task = self.get_task(task_id)
        if not task:
            raise ValueError("未找到录音分析任务。")
        if isinstance(task.get("result"), dict):
            task["result"]["review_status"] = "rejected"
        task["review_status"] = "rejected"
        self.save_task(task)
        log = self._append_log(task_id, reviewer=reviewer, action="reject", detail={"reason": reason})
        return {"success": True, "task": task, "review_log": log}

    def update(self, task_id: str, *, reviewer: str = "讲师", updates: list[dict[str, Any]]) -> dict[str, Any]:
        task = self.get_task(task_id)
        if not task or not isinstance(task.get("result"), dict):
            raise ValueError("未找到可编辑的录音分析任务。")
        task["result"]["qa_analysis"] = self._apply_updates(task["result"].get("qa_analysis") or [], updates)
        task["review_status"] = "pending_review"
        task["result"]["review_status"] = "pending_review"
        self.save_task(task)
        log = self._append_log(task_id, reviewer=reviewer, action="update", detail={"updates": updates})
        return {"success": True, "task": task, "review_log": log}

    def logs(self, task_id: str | None = None) -> list[dict[str, Any]]:
        logs = self._load_logs()
        if task_id:
            return [item for item in logs if item.get("task_id") == task_id]
        return logs

    def _apply_updates(self, qa_analysis: list[dict[str, Any]], updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_id = {str(item.get("question_id") or item.get("id") or index): item for index, item in enumerate(qa_analysis)}
        for update in updates:
            question_id = str(update.get("question_id") or "")
            if not question_id or question_id not in by_id:
                continue
            item = by_id[question_id]
            if update.get("question") is not None:
                item["question"] = str(update["question"])
            if update.get("standard_answer") is not None:
                item["standard_answer"] = str(update["standard_answer"])
            if update.get("knowledge_points") is not None:
                item["knowledge_points"] = update["knowledge_points"]
        return qa_analysis

    def _format_ingest_text(self, qa_analysis: list[dict[str, Any]], *, reviewer: str) -> str:
        now = self._now()
        blocks = []
        for item in qa_analysis:
            question = str(item.get("question") or "").strip()
            answer = str(item.get("standard_answer") or "").strip()
            if not question or not answer:
                continue
            knowledge_points = item.get("knowledge_points") or item.get("missing_points") or []
            blocks.append(
                "\n".join(
                    [
                        "真实面试题：",
                        f"问题：{question}",
                        f"知识点：{', '.join(str(point) for point in knowledge_points) if isinstance(knowledge_points, list) else knowledge_points}",
                        f"标准答案：{answer}",
                        f"常见错误回答：{'; '.join(str(point) for point in item.get('wrong_points') or [])}",
                        f"评分要点：{'; '.join(str(point) for point in item.get('correct_points') or [])}",
                        "来源：面试录音审核收录",
                        f"审核人：{reviewer}",
                        f"审核时间：{now}",
                    ]
                )
            )
        return "\n\n---\n\n".join(blocks) or "面试录音审核未产生可入库题目。"

    def _append_log(self, task_id: str, *, reviewer: str, action: str, detail: dict[str, Any]) -> dict[str, Any]:
        logs = self._load_logs()
        log = {
            "log_id": str(uuid.uuid4()),
            "task_id": task_id,
            "reviewer": reviewer,
            "action": action,
            "detail": detail,
            "created_at": self._now(),
        }
        logs.append(log)
        self.logs_path.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")
        return log

    def _load_tasks(self) -> dict[str, Any]:
        if not self.tasks_path.exists():
            return {}
        try:
            return json.loads(self.tasks_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _load_logs(self) -> list[dict[str, Any]]:
        if not self.logs_path.exists():
            return []
        try:
            data = json.loads(self.logs_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def _now(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _matches_audio(
        self,
        task: dict[str, Any],
        *,
        audio_file_id: str | None,
        audio_url: str | None,
        audio_sha256: str | None,
    ) -> bool:
        if audio_file_id and task.get("audio_file_id") == audio_file_id:
            return True
        if audio_url and task.get("audio_url") == audio_url:
            return True
        if audio_sha256:
            task_hash = str(task.get("audio_sha256") or "") or self._audio_hash_from_file_id(str(task.get("audio_file_id") or ""))
            return task_hash == audio_sha256
        return False

    def _audio_hash_from_file_id(self, file_id: str) -> str:
        if not file_id:
            return ""
        index_path = Path(__file__).resolve().parents[2] / "uploads" / "file_index.json"
        if not index_path.exists():
            return ""
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return ""
        record = index.get(file_id) if isinstance(index, dict) else None
        if not isinstance(record, dict):
            return ""
        existing = str(record.get("file_sha256") or "")
        if existing:
            return existing
        path = Path(str(record.get("file_path") or ""))
        if not path.exists():
            return ""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


audio_review_service = AudioReviewService()
