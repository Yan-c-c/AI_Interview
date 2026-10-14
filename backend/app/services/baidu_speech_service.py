from __future__ import annotations

import base64
import json
import os
import time
import urllib.parse
import urllib.request

from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


class BaiduSpeechError(RuntimeError):
    pass


class BaiduSpeechService:
    """Small Baidu speech REST client used by the mock interview voice flow."""

    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    ASR_URL = "https://vop.baidu.com/server_api"
    TTS_URL = "https://tsn.baidu.com/text2audio"

    def __init__(self) -> None:
        self.api_key = os.getenv("BAIDU_SPEECH_API_KEY") or os.getenv("BAIDU_APP_KEY") or ""
        self.secret_key = os.getenv("BAIDU_SPEECH_SECRET_KEY") or os.getenv("BAIDU_SECRET_KEY") or ""
        self.cuid = os.getenv("BAIDU_SPEECH_APP_ID") or "ai_interview_assistant"
        self._access_token = ""
        self._token_expires_at = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.secret_key)

    def _request_json(self, request: urllib.request.Request, timeout: int = 30) -> dict:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise BaiduSpeechError(f"百度语音接口返回非 JSON：{payload[:120]}") from exc
        if not isinstance(data, dict):
            raise BaiduSpeechError("百度语音接口返回格式异常")
        return data

    def _ensure_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        if not self.configured:
            raise BaiduSpeechError("未配置百度语音 API Key 或 Secret Key")

        query = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key,
            }
        )
        request = urllib.request.Request(f"{self.TOKEN_URL}?{query}", method="POST")
        data = self._request_json(request, timeout=12)
        token = str(data.get("access_token") or "")
        if not token:
            raise BaiduSpeechError(f"获取百度语音 token 失败：{data}")
        self._access_token = token
        self._token_expires_at = time.time() + int(data.get("expires_in") or 2592000) - 60
        return token

    def speech_to_text(self, audio_data: bytes, *, audio_format: str = "pcm", rate: int = 16000) -> str:
        if not audio_data:
            raise BaiduSpeechError("音频内容为空")
        token = self._ensure_token()
        payload = {
            "format": audio_format,
            "rate": rate,
            "channel": 1,
            "cuid": self.cuid,
            "token": token,
            "speech": base64.b64encode(audio_data).decode("utf-8"),
            "len": len(audio_data),
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.ASR_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        data = self._request_json(request)
        if data.get("err_no") == 0 and data.get("result"):
            return str(data["result"][0]).strip()
        raise BaiduSpeechError(f"百度语音识别失败：err_no={data.get('err_no')}, msg={data.get('err_msg')}")



baidu_speech_service = BaiduSpeechService()
