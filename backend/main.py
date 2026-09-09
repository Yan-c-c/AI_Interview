from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, assistant, upload

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

LOCAL_DEV_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"
CORS_ALLOW_ORIGIN_REGEX = os.getenv("CORS_ALLOW_ORIGIN_REGEX", LOCAL_DEV_ORIGIN_REGEX)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("智能面试助手后端启动")
    yield
    logger.info("智能面试助手后端关闭")


app = FastAPI(
    title="智能面试助手 API",
    description="简历评估 Agent 与面试题生成 Agent 已实现，其他 Agent 预留。",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict:
    return {"message": "智能面试助手 API", "status": "running", "docs": "/docs"}


@app.get("/health")
async def health_check() -> dict:
    return {"status": "healthy"}


app.include_router(upload.router)
app.include_router(assistant.router)
app.include_router(admin.router)
