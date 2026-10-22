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








    def _load_tasks(self) -> dict[str, Any]:
        if not self.tasks_path.exists():
            return {}
        try:
            return json.loads(self.tasks_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}


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
