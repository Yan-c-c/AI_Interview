"""OpenAI-compatible LLM factory.

The reference project used ``langchain_openai.ChatOpenAI`` with per-request
configuration. This version keeps that behavior and adds environment based
DeepSeek/OpenAI-compatible defaults for the assistant APIs.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


CHANNEL_ALIASES = {
    "matching_analyst": "smart",
    "content_optimizer": "smart",
    "content_writer": "smart",
    "hr_reviewer": "smart",
    "risk_template_reviewer": "smart",
    "reflector": "smart",
    "general": "smart",
    "smart": "smart",
    "fast": "fast",
}


def create_llm_from_config(
    api_key: str,
    base_url: str,
    model: str,
    temperature: float = 0.2,
    max_tokens: int = 8000,
) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model_name=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _get_nested_config(api_config: dict[str, Any], channel: str) -> Optional[dict[str, Any]]:
    channel_key = CHANNEL_ALIASES.get(channel, channel)
    if channel_key in api_config and isinstance(api_config[channel_key], dict):
        return api_config[channel_key]
    if channel in api_config and isinstance(api_config[channel], dict):
        return api_config[channel]
    if {"api_key", "base_url", "model"}.issubset(api_config.keys()):
        return api_config
    return None


def _get_env_config(channel: str) -> Optional[dict[str, str]]:
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if deepseek_key:
        return {
            "api_key": deepseek_key,
            "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        }

    if openai_key:
        model_env = "FAST_MODEL" if CHANNEL_ALIASES.get(channel) == "fast" else "SMART_MODEL"
        return {
            "api_key": openai_key,
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "model": os.getenv(model_env) or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        }

    return None


def get_llm_for_request(
    api_config: Optional[dict[str, Any]] = None,
    channel: str = "smart",
    temperature: float = 0.2,
    max_tokens: int = 8000,
) -> ChatOpenAI:
    config = _get_nested_config(api_config or {}, channel) if api_config else None
    if not config:
        config = _get_env_config(channel)

    if not config or not config.get("api_key"):
        raise ValueError(
            "未检测到可用的大模型 API 配置。请设置 DEEPSEEK_API_KEY，"
            "或在后端 .env 中设置 OpenAI 兼容 API 配置。"
        )

    return create_llm_from_config(
        api_key=config["api_key"],
        base_url=config.get("base_url") or config.get("baseURL") or "https://api.deepseek.com",
        model=config.get("model") or "deepseek-chat",
        temperature=temperature,
        max_tokens=max_tokens,
    )
