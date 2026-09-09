from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import uuid
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

logger = logging.getLogger(__name__)


class FileParserError(Exception):
    pass


class UnsupportedFileTypeError(FileParserError):
    pass


@dataclass
class ParsedFileRecord:
    file_id: str
    filename: str
    file_type: str
    parsed_text: str
    parsed_char_count: int
    file_path: str = ""
    is_audio: bool = False
    file_sha256: str = ""


class FileParserService:
    """Parse uploaded resumes into markdown-like text for LLM processing."""

    allowed_extensions = {"pdf", "docx", "txt", "md", "mp3", "wav", "m4a", "amr", "pcm", "flac", "aac", "ogg"}
    audio_extensions = {"mp3", "wav", "m4a", "amr", "pcm", "flac", "aac", "ogg"}

    def __init__(self, storage_dir: Optional[Path] = None, max_size_mb: int = 120):
        base_dir = Path(__file__).resolve().parents[2]
        self.storage_dir = storage_dir or base_dir / "uploads"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_dir / "file_index.json"
        self.max_size_bytes = max_size_mb * 1024 * 1024

    async def parse_upload(self, upload_file: UploadFile) -> ParsedFileRecord:
        filename = upload_file.filename or "resume"
        file_ext = Path(filename).suffix.lower().lstrip(".")
        if file_ext not in self.allowed_extensions:
            raise UnsupportedFileTypeError(
                f"不支持的文件格式: {file_ext or 'unknown'}。支持: {', '.join(sorted(self.allowed_extensions))}"
            )

        size = upload_file.size
        if size is not None and size > self.max_size_bytes:
            raise FileParserError(f"文件超过 {self.max_size_bytes // 1024 // 1024}MB 限制")

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as temp:
            temp_path = Path(temp.name)
            try:
                shutil.copyfileobj(upload_file.file, temp)
            finally:
                upload_file.file.close()

        file_id = str(uuid.uuid4())
        is_audio = file_ext in self.audio_extensions
        file_path = ""
        file_sha256 = self._sha256_file(temp_path)
        try:
            if temp_path.stat().st_size > self.max_size_bytes:
                raise FileParserError(f"文件超过 {self.max_size_bytes // 1024 // 1024}MB 限制")
            target_path = self.storage_dir / f"{file_id}.{file_ext}"
            if is_audio:
                shutil.copyfile(temp_path, target_path)
                parsed_text = ""
            else:
                parsed_text = self.parse_path(temp_path, file_ext)
                shutil.copyfile(temp_path, target_path)
            file_path = str(target_path)
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("临时文件删除失败: %s", exc)

        if not is_audio and not parsed_text.strip():
            raise FileParserError("文件解析后内容为空")

        record = ParsedFileRecord(
            file_id=file_id,
            filename=filename,
            file_type=file_ext,
            parsed_text=parsed_text.strip(),
            parsed_char_count=len(parsed_text.strip()),
            file_path=file_path,
            is_audio=is_audio,
            file_sha256=file_sha256,
        )
        self.save_record(record)
        return record

    def parse_path(self, path: Path, file_ext: Optional[str] = None) -> str:
        ext = (file_ext or path.suffix.lower().lstrip(".")).lower()

        if ext in {"txt", "md"}:
            return self._parse_text(path)
        raise UnsupportedFileTypeError(f"不支持的文件格式: {ext}")




    def _parse_text(self, path: Path) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise FileParserError("无法识别文本编码")

    def _load_index(self) -> dict[str, dict]:
        if not self.index_path.exists():
            return {}
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def save_record(self, record: ParsedFileRecord) -> None:
        index = self._load_index()
        index[record.file_id] = asdict(record)
        self.index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_record(self, file_id: str) -> Optional[ParsedFileRecord]:
        data = self._load_index().get(file_id)
        if not data:
            return None
        return ParsedFileRecord(**data)

    def _sha256_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


file_parser_service = FileParserService()
