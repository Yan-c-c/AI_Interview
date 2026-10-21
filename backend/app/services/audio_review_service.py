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




audio_review_service = AudioReviewService()
