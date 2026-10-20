from __future__ import annotations

import mimetypes
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


class AliyunOSSError(RuntimeError):
    pass


@dataclass(frozen=True)
class AliyunOSSUploadResult:
    object_key: str
    public_url: str
    signed_url: str
    bucket: str
    endpoint: str
    expires_seconds: int
    raw: dict[str, Any]


class AliyunOSSService:
    """Upload local interview audio files to OSS and create Baidu-accessible URLs."""

    def __init__(self) -> None:
        self.access_key_id = os.getenv("ALIYUN_OSS_ACCESS_KEY_ID") or os.getenv("OSS_ACCESS_KEY_ID") or ""
        self.access_key_secret = os.getenv("ALIYUN_OSS_ACCESS_KEY_SECRET") or os.getenv("OSS_ACCESS_KEY_SECRET") or ""
        self.bucket_name = os.getenv("ALIYUN_OSS_BUCKET") or os.getenv("OSS_BUCKET") or ""
        self.region = os.getenv("ALIYUN_OSS_REGION") or os.getenv("OSS_REGION") or ""
        self.endpoint = (os.getenv("ALIYUN_OSS_ENDPOINT") or self._endpoint_from_region(self.region)).rstrip("/")
        self.prefix = (os.getenv("ALIYUN_OSS_PREFIX") or "interview-audio/").strip().strip("/")
        self.expires_seconds = int(os.getenv("ALIYUN_OSS_SIGNED_URL_EXPIRES_SECONDS") or "7200")
        self.public_read = (os.getenv("ALIYUN_OSS_PUBLIC_READ") or "0") == "1"

    @property
    def configured(self) -> bool:
        return bool(self.access_key_id and self.access_key_secret and self.bucket_name and self.endpoint)

    def upload_file(self, path: Path, *, filename: str | None = None) -> AliyunOSSUploadResult:
        if not self.configured:
            raise AliyunOSSError("未配置阿里云 OSS AccessKey、Bucket 或 Endpoint。")
        if not path.exists():
            raise AliyunOSSError(f"本地音频文件不存在：{path}")

        try:
            import oss2  # type: ignore
        except Exception as exc:
            raise AliyunOSSError("缺少 oss2 依赖，请先安装 requirements.txt。") from exc

        safe_name = self._safe_filename(filename or path.name)
        date_prefix = datetime.now().strftime("%Y%m%d")
        object_key = f"{self.prefix}/{date_prefix}/{uuid.uuid4().hex[:12]}-{safe_name}" if self.prefix else f"{date_prefix}/{uuid.uuid4().hex[:12]}-{safe_name}"
        object_key = object_key.replace("//", "/")
        content_type = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"

        auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
        headers = {"Content-Type": content_type}
        result = bucket.put_object_from_file(object_key, str(path), headers=headers)
        signed_url = bucket.sign_url("GET", object_key, self.expires_seconds, slash_safe=True)
        public_url = self._public_url(object_key)
        return AliyunOSSUploadResult(
            object_key=object_key,
            public_url=public_url,
            signed_url=public_url if self.public_read else signed_url,
            bucket=self.bucket_name,
            endpoint=self.endpoint,
            expires_seconds=self.expires_seconds,
            raw={
                "status": getattr(result, "status", None),
                "request_id": getattr(result, "request_id", None),
                "etag": getattr(result, "etag", None),
            },
        )

    def _endpoint_from_region(self, region: str) -> str:
        return f"https://{region}.aliyuncs.com" if region else ""

    def _public_url(self, object_key: str) -> str:
        host = self.endpoint.replace("https://", "").replace("http://", "")
        scheme = "https" if self.endpoint.startswith("https://") else "http"
        return f"{scheme}://{self.bucket_name}.{host}/{object_key}"

    def _safe_filename(self, filename: str) -> str:
        name = Path(filename).name or "interview-audio.mp3"
        return re.sub(r"[^\w\u4e00-\u9fff.\-()（） ]+", "_", name)


aliyun_oss_service = AliyunOSSService()
