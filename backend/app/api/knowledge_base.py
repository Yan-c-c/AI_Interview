from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.services.auth_service import require_admin
from app.services.knowledge_base import knowledge_base_service

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"], dependencies=[Depends(require_admin)])


class KnowledgeQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="检索问题或关键词")
    mode: str | None = Field(default=None, description="检索模式，默认读取后端配置")
    top_k: int | None = Field(default=None, ge=1, le=30)


class KnowledgeTextRequest(BaseModel):
    title: str | None = Field(default=None, max_length=160)
    text: str = Field(..., min_length=1)




@router.get("/documents")
async def list_documents() -> dict[str, Any]:
    documents = await knowledge_base_service.list_documents()
    return {"success": True, "documents": documents, "total": len(documents)}


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        document = await knowledge_base_service.upload_document(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": f"文档写入失败：{exc}"}) from exc
    return {"success": True, "document": document}


@router.post("/documents/text")
async def insert_text(request: KnowledgeTextRequest) -> dict[str, Any]:
    try:
        document = await knowledge_base_service.insert_text(title=request.title, text=request.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return {"success": True, "document": document}


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str) -> dict[str, Any]:
    deleted = await knowledge_base_service.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail={"message": "未找到该知识库文档。"})
    return {"success": True, "deleted": True, "document_id": document_id}






