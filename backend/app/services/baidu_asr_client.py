from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


class BaiduASRError(RuntimeError):
    pass


class BaiduASRQuotaLimitError(BaiduASRError):
    pass


class BaiduASRTaskPendingError(BaiduASRError):
    def __init__(self, task_id: str, last_result: dict[str, Any]) -> None:
        super().__init__("百度音频文件转写仍在处理中，请稍后刷新获取结果。")
        self.task_id = task_id
        self.last_result = last_result


@dataclass(frozen=True)
class BaiduASRConfig:
    api_key: str
    secret_key: str
    base_url: str
    pid: int
    rate: int
    audio_format: str
    poll_interval_seconds: float
    poll_timeout_seconds: float


class BaiduASRClient:
    """Baidu audio-file transcription client for asynchronous ASR tasks."""

    TOKEN_PATH = "/oauth/2.0/token"
    CREATE_PATH = "/rpc/2.0/aasr/v1/create"
    QUERY_PATH = "/rpc/2.0/aasr/v1/query"

    def __init__(self) -> None:
        self.config = BaiduASRConfig(
            api_key=os.getenv("BAIDU_ASR_API_KEY") or os.getenv("BAIDU_SPEECH_API_KEY") or "",
            secret_key=os.getenv("BAIDU_ASR_SECRET_KEY") or os.getenv("BAIDU_SPEECH_SECRET_KEY") or "",
            base_url=(os.getenv("BAIDU_ASR_BASE_URL") or "https://aip.baidubce.com").rstrip("/"),
            pid=int(os.getenv("BAIDU_ASR_PID") or "8953"),
            rate=int(os.getenv("BAIDU_ASR_RATE") or "16000"),
            audio_format=os.getenv("BAIDU_ASR_FORMAT") or "mp3",
            poll_interval_seconds=float(os.getenv("BAIDU_ASR_POLL_INTERVAL_SECONDS") or "3"),
            poll_timeout_seconds=float(os.getenv("BAIDU_ASR_POLL_TIMEOUT_SECONDS") or "45"),
        )
        self._access_token = ""
        self._token_expires_at = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.config.api_key and self.config.secret_key)

    def create_task(self, speech_url: str, *, audio_format: str | None = None, rate: int | None = None) -> dict[str, Any]:
        if not speech_url:
            raise BaiduASRError("音频文件转写需要可公网访问的 speech_url。")
        token = self._ensure_token()
        payload = {
            "speech_url": speech_url,
            "format": audio_format or self.config.audio_format,
            "pid": self.config.pid,
            "rate": rate or self.config.rate,
        }
        data = self._post_json(f"{self.config.base_url}{self.CREATE_PATH}?access_token={token}", payload)
        if data.get("error_code") == 336204:
            raise BaiduASRQuotaLimitError(
                "百度音频文件转写总请求额度已用完或达到总请求限制。请到百度智能云控制台检查音频文件转写额度，"
                "更换可用应用 Key，或等待额度重置后重试。"
            )
        if data.get("error_code"):
            raise BaiduASRError(f"百度音频转写任务创建失败：{data}")
        task_id = data.get("task_id") or data.get("taskId")
        if not task_id:
            raise BaiduASRError(f"百度音频转写任务创建失败：{data}")
        data["task_id"] = task_id
        return data

    def query_task(self, task_id: str) -> dict[str, Any]:
        if not task_id:
            raise BaiduASRError("缺少百度音频转写 task_id。")
        token = self._ensure_token()
        payload = {"task_ids": [task_id]}
        data = self._post_json(f"{self.config.base_url}{self.QUERY_PATH}?access_token={token}", payload)
        return data

    def wait_for_result(self, task_id: str, *, timeout_seconds: float | None = None) -> dict[str, Any]:
        deadline = time.time() + (timeout_seconds if timeout_seconds is not None else self.config.poll_timeout_seconds)
        last_result: dict[str, Any] = {}
        while time.time() <= deadline:
            last_result = self.query_task(task_id)
            status = self._extract_task_status(last_result)
            if status in {"success", "finished", "completed", "done"}:
                return last_result
            if status in {"failure", "failed", "error"}:
                raise BaiduASRError(f"百度音频转写任务失败：{last_result}")
            time.sleep(self.config.poll_interval_seconds)
        last_result.setdefault("status", "running")
        raise BaiduASRTaskPendingError(task_id, last_result)

    def task_status(self, data: dict[str, Any]) -> str:
        return self._extract_task_status(data)

    def normalize_result(self, result: dict[str, Any]) -> dict[str, Any]:
        task_result = self._first_task_result(result)
        raw_segments = self._extract_segments(task_result)
        segments: list[dict[str, Any]] = []
        for index, item in enumerate(raw_segments):
            text = self._segment_text(item)
            if not text:
                continue
            speaker = self._segment_speaker(item, index)
            start_ms = self._segment_time(item, "start_time", "begin_time", "start", "bg")
            end_ms = self._segment_time(item, "end_time", "finish_time", "end", "ed")
            segments.append(
                {
                    "segment_id": f"s{len(segments) + 1}",
                    "speaker": speaker,
                    "text": text,
                    "start_time": self._format_time(start_ms),
                    "end_time": self._format_time(end_ms),
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "raw": item,
                }
            )
        raw_text = "\n".join(f"{item['speaker']} {item['start_time']}: {item['text']}" for item in segments)
        return {"raw_text": raw_text, "segments": segments, "raw_result": result}

    def _ensure_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        if not self.configured:
            raise BaiduASRError("未配置百度音频文件转写 API Key 或 Secret Key")
        query = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self.config.api_key,
                "client_secret": self.config.secret_key,
            }
        )
        request = urllib.request.Request(f"{self.config.base_url}{self.TOKEN_PATH}?{query}", method="POST")
        data = self._request_json(request, timeout=12)
        token = str(data.get("access_token") or "")
        if not token:
            raise BaiduASRError(f"获取百度 ASR token 失败：{data}")
        self._access_token = token
        self._token_expires_at = time.time() + int(data.get("expires_in") or 2592000) - 60
        return token

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        return self._request_json(request, timeout=30)

    def _request_json(self, request: urllib.request.Request, timeout: int = 30) -> dict[str, Any]:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise BaiduASRError(f"百度音频文件转写接口返回非 JSON：{payload[:160]}") from exc
        if not isinstance(data, dict):
            raise BaiduASRError("百度音频文件转写接口返回格式异常")
        return data

    def _extract_task_status(self, data: dict[str, Any]) -> str:
        task = self._first_task_result(data)
        for key in ("task_status", "status", "status_text", "taskStatus"):
            if task.get(key) is not None:
                return str(task[key]).lower()
        return str(data.get("status") or "running").lower()

    def _first_task_result(self, data: dict[str, Any]) -> dict[str, Any]:
        for key in ("tasks_info", "tasks", "result", "results"):
            value = data.get(key)
            if isinstance(value, list) and value:
                return value[0] if isinstance(value[0], dict) else {"result": value[0]}
            if isinstance(value, dict):
                return value
        return data

    def _extract_segments(self, data: dict[str, Any]) -> list[Any]:
        task_result = data.get("task_result")
        if isinstance(task_result, dict):
            nested = self._extract_segments(task_result)
            if nested:
                return nested
        for key in ("detailed_result", "detailed_results", "segments", "sentences", "result", "transcription_text"):
            value = data.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = value.get("segments") or value.get("sentences") or value.get("detailed_result")
                if isinstance(nested, list):
                    return nested
            if isinstance(value, str):
                return [{"text": value}]
        return []

    def _segment_text(self, item: Any) -> str:
        if isinstance(item, str):
            return item.strip()
        if not isinstance(item, dict):
            return ""
        value = item.get("text") or item.get("sentence") or item.get("res") or item.get("onebest") or item.get("result")
        if isinstance(value, list):
            return "".join(str(part) for part in value).strip()
        return str(value or "").strip()

    def _segment_speaker(self, item: Any, index: int) -> str:
        if isinstance(item, dict):
            for key in ("speaker", "speaker_id", "spk", "role", "channel_id"):
                if item.get(key) is not None:
                    raw = str(item[key])
                    return raw if raw.startswith("speaker_") else f"speaker_{raw}"
        return f"speaker_{index % 2}"

    def _segment_time(self, item: Any, *keys: str) -> int:
        if not isinstance(item, dict):
            return 0
        for key in keys:
            if item.get(key) is not None:
                try:
                    return int(float(item[key]))
                except (TypeError, ValueError):
                    return 0
        return 0

    def _format_time(self, milliseconds: int) -> str:
        seconds = max(0, milliseconds // 1000)
        hour = seconds // 3600
        minute = (seconds % 3600) // 60
        second = seconds % 60
        if hour:
            return f"{hour:02d}:{minute:02d}:{second:02d}"
        return f"{minute:02d}:{second:02d}"


baidu_asr_client = BaiduASRClient()
