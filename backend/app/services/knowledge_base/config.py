from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BACKEND_DIR / ".env")
load_dotenv()


def _path_from_env(name: str, default: str) -> Path:
    value = os.getenv(name) or default
    path = Path(value)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class KnowledgeBaseConfig:
    base_url: str = (os.getenv("LIGHTRAG_BASE_URL") or "http://127.0.0.1:9621").rstrip("/")
    api_key: str = os.getenv("LIGHTRAG_API_KEY") or ""
    query_mode: str = os.getenv("LIGHTRAG_QUERY_MODE") or "mix"
    timeout_seconds: float = float(os.getenv("LIGHTRAG_TIMEOUT_SECONDS") or "8")
    top_k: int = int(os.getenv("LIGHTRAG_TOP_K") or "8")
    chunk_top_k: int = int(os.getenv("LIGHTRAG_CHUNK_TOP_K") or os.getenv("LIGHTRAG_TOP_K") or "8")
    input_dir: Path = _path_from_env("LIGHTRAG_INPUT_DIR", "data/interview_kb/inputs")
    working_dir: Path = _path_from_env("LIGHTRAG_WORKING_DIR", "data/interview_kb/rag_storage")
    max_graph_nodes: int = int(os.getenv("LIGHTRAG_MAX_GRAPH_NODES") or "500")
    summary_language: str = os.getenv("LIGHTRAG_SUMMARY_LANGUAGE") or "Chinese"
    chunk_size: int = int(os.getenv("LIGHTRAG_CHUNK_SIZE") or "1200")
    chunk_overlap_size: int = int(os.getenv("LIGHTRAG_CHUNK_OVERLAP_SIZE") or "100")


knowledge_base_config = KnowledgeBaseConfig()
