from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SALARY_DIR = BACKEND_DIR / "data" / "salary_system"


def _path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return path.resolve()


def salary_data_dir() -> Path:
    return _path(os.getenv("SALARY_DATA_PATH") or DEFAULT_SALARY_DIR)


def salary_processed_dir() -> Path:
    explicit = os.getenv("SALARY_PROCESSED_DATA_PATH")
    return _path(explicit) if explicit else salary_data_dir() / "processed"


def salary_models_dir() -> Path:
    explicit = os.getenv("SALARY_MODEL_DIR")
    return _path(explicit) if explicit else salary_data_dir() / "models"


def salary_model_path() -> Path:
    return _path(os.getenv("SALARY_MODEL_PATH") or salary_models_dir() / "xgboost_optimized.pkl")


def salary_trend_model_path() -> Path:
    return _path(os.getenv("SALARY_TREND_MODEL_PATH") or salary_models_dir() / "lstm_trend.keras")


def salary_rl_model_path() -> Path:
    return _path(os.getenv("SALARY_RL_MODEL_PATH") or salary_models_dir() / "rl_negotiation")


def salary_word2vec_model_path() -> Path:
    return _path(os.getenv("SALARY_WORD2VEC_MODEL_PATH") or salary_processed_dir() / "skills_word2vec.model")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
