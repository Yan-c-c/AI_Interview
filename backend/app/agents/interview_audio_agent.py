from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base_agent import BaseAgent
from app.core.json_utils import loads_json_response
from app.core.llms import get_llm_for_request
from app.schemas.agent_schema import AgentRequest, AgentResponse
from app.services.audio_review_service import audio_review_service
from app.services.audio_transcription_service import audio_transcription_service
from app.services.baidu_asr_client import BaiduASRError, BaiduASRQuotaLimitError, BaiduASRTaskPendingError, baidu_asr_client
from app.services.file_parser_service import ParsedFileRecord
from app.services.public_answer_search_service import public_answer_search_service

logger = logging.getLogger(__name__)


class InterviewAudioAnalysisAgent(BaseAgent):
    name = "interview_audio_analysis_agent"
    task_type = "interview_audio_analysis"

    async def run(self, request: AgentRequest) -> AgentResponse:
        record = request.metadata.get("file_record")
        if isinstance(record, dict):
            record = ParsedFileRecord(**record)
        transcript_text = str(request.metadata.get("transcript_text") or "").strip()
        if transcript_text and not record:
            filename = request.filename or "粘贴面试对话"
            task = audio_review_service.create_task(
                audio_filename=filename,
                audio_file_id=None,
                audio_url=None,
                audio_sha256=None,
            )
            task["status"] = "transcribed"
            task["review_status"] = "text_analysis"
            audio_review_service.save_task(task)
            return await self._complete_analysis(
                request=request,
                task_id=task["task_id"],
                transcript=self._transcript_from_text(transcript_text),
                filename=filename,
                audio_file_id=None,
                audio_url=None,
                audio_sha256=None,
                text_transcript=True,
            )
        if record and not getattr(record, "is_audio", False):
            return self._error("uploaded_file_not_audio", "请上传面试录音文件，例如 mp3、wav、m4a。")

        audio_url = request.metadata.get("audio_url")
        filename = request.filename or (record.filename if record else "") or "面试录音"
        audio_sha256 = getattr(record, "file_sha256", "") if record else ""
        reusable = audio_review_service.find_reusable_task(audio_file_id=request.file_id, audio_url=audio_url, audio_sha256=audio_sha256)
        if reusable:
            result = reusable.get("result")
            if not isinstance(result, dict) and reusable.get("status") in {"created", "transcribing", "transcribed"}:
                result = self._processing_result(
                    task_id=reusable["task_id"],
                    filename=str(reusable.get("audio_filename") or filename),
                    audio_file_id=reusable.get("audio_file_id"),
                    audio_url=reusable.get("audio_url"),
                    audio_sha256=reusable.get("audio_sha256") or audio_sha256,
                    baidu_task_id=str(reusable.get("baidu_task_id") or ""),
                    raw_result=reusable.get("raw_baidu_result") if isinstance(reusable.get("raw_baidu_result"), dict) else {},
                )
                reusable["result"] = result
                audio_review_service.save_task(reusable)
            if isinstance(result, dict):
                message = "已复用该录音的百度转写任务，请点击刷新结果继续查询。" if reusable.get("status") in {"created", "transcribing", "transcribed"} else "已复用该录音的历史分析结果。"
                status = "transcribing" if reusable.get("status") in {"created", "transcribing", "transcribed"} else None
                result["audio_cache_hit"] = True
                result.setdefault("metadata", {})["audio_sha256"] = reusable.get("audio_sha256") or audio_sha256
                result.setdefault("metadata", {})["reused_audio_task"] = True
                result.setdefault("metadata", {})["reused_task_id"] = reusable["task_id"]
                audio_review_service.save_task(reusable)
                return AgentResponse(
                    success=True,
                    agent=self.name,
                    task_type=self.task_type,
                    status=status,
                    message=message,
                    result={"success": True, "task_id": reusable["task_id"], "task": reusable, **result},
                )
            return AgentResponse(
                success=True,
                agent=self.name,
                task_type=self.task_type,
                message="已复用该录音的历史分析结果。",
                result={"success": True, "task_id": reusable["task_id"], "task": reusable, **result},
            )
        task = audio_review_service.create_task(
            audio_filename=filename,
            audio_file_id=request.file_id,
            audio_url=audio_url,
            audio_sha256=audio_sha256,
        )
        task_id = task["task_id"]

        try:
            transcript = await audio_transcription_service.transcribe(record=record, audio_url=audio_url)
            task["status"] = "transcribed"
            task["baidu_task_id"] = transcript.get("baidu_task_id")
            audio_review_service.save_task(task)
            return await self._complete_analysis(
                request=request,
                task_id=task_id,
                transcript=transcript,
                filename=filename,
                audio_file_id=request.file_id,
                audio_url=audio_url,
                audio_sha256=audio_sha256,
            )
        except BaiduASRTaskPendingError as exc:
            task["status"] = "transcribing"
            task["review_status"] = "transcribing"
            task["baidu_task_id"] = exc.task_id
            task["raw_baidu_result"] = exc.last_result
            result = self._processing_result(
                task_id=task_id,
                filename=filename,
                audio_file_id=request.file_id,
                audio_url=audio_url,
                audio_sha256=audio_sha256,
                baidu_task_id=exc.task_id,
                raw_result=exc.last_result,
            )
            task["result"] = result
            audio_review_service.save_task(task)
            return AgentResponse(
                success=True,
                agent=self.name,
                task_type=self.task_type,
                status="transcribing",
                message="百度音频文件转写仍在处理中，请稍后点击刷新获取转写和分析结果。",
                result={"success": True, "task_id": task_id, "task": task, **result},
            )
        except BaiduASRQuotaLimitError as exc:
            failed = audio_review_service.fail_task(task_id, str(exc))
            return AgentResponse(
                success=False,
                agent=self.name,
                task_type=self.task_type,
                message=str(exc),
                result={
                    "success": False,
                    "task_id": task_id,
                    "status": "failed",
                    "error": "baidu_asr_quota_limit",
                    "message": str(exc),
                    "task": failed,
                },
            )
        except BaiduASRError as exc:
            failed = audio_review_service.fail_task(task_id, str(exc))
            return AgentResponse(
                success=False,
                agent=self.name,
                task_type=self.task_type,
                message=str(exc),
                result={"success": False, "task_id": task_id, "status": "failed", "task": failed},
            )
        except Exception as exc:
            logger.exception("audio transcription failed")
            failed = audio_review_service.fail_task(task_id, f"音频转写失败：{exc}")
            return AgentResponse(
                success=False,
                agent=self.name,
                task_type=self.task_type,
                message="音频转写失败，请检查百度音频文件转写配置。",
                result={"success": False, "task_id": task_id, "status": "failed", "task": failed},
            )

    async def continue_task(self, task_id: str) -> dict[str, Any]:
        task = audio_review_service.get_task(task_id)
        if not task:
            return {"success": False, "message": "未找到录音分析任务。"}
        result = task.get("result")
        if isinstance(result, dict) and (result.get("qa_analysis") or (result.get("transcript") or {}).get("raw_text")):
            return {"success": True, "task": task, "result": result}
        baidu_task_id = str(task.get("baidu_task_id") or "")
        if not baidu_task_id:
            return {"success": True, "task": task, "result": result}
        raw_result = await asyncio.to_thread(baidu_asr_client.query_task, baidu_task_id)
        status = baidu_asr_client.task_status(raw_result)
        if status in {"running", "created", "pending"}:
            task["status"] = "transcribing"
            task["review_status"] = "transcribing"
            task["raw_baidu_result"] = raw_result
            if isinstance(result, dict):
                result["status"] = "transcribing"
                result["raw_baidu_result"] = raw_result
                task["result"] = result
            audio_review_service.save_task(task)
            return {"success": True, "task": task, "result": task.get("result")}
        if status in {"failure", "failed", "error"}:
            failed = audio_review_service.fail_task(task_id, f"百度音频转写任务失败：{raw_result}")
            return {"success": False, "task": failed, "result": failed.get("result"), "message": failed.get("error")}
        transcript = baidu_asr_client.normalize_result(raw_result)
        transcript["baidu_task_id"] = baidu_task_id
        transcript["raw_result"] = raw_result
        if not transcript.get("raw_text") and not transcript.get("segments"):
            task["status"] = "transcription_empty"
            task["review_status"] = "analysis_failed"
            task["raw_baidu_result"] = raw_result
            task["error"] = "百度任务已成功，但返回结果中没有可解析的转写文本。"
            audio_review_service.save_task(task)
            return {"success": False, "task": task, "result": task.get("result"), "message": task["error"]}
        request = AgentRequest(
            message="继续完成面试录音分析",
            file_id=task.get("audio_file_id"),
            filename=task.get("audio_filename"),
            metadata={"audio_url": task.get("audio_url")},
        )
        response = await self._complete_analysis(
            request=request,
            task_id=task_id,
            transcript=transcript,
            filename=str(task.get("audio_filename") or "面试录音"),
            audio_file_id=task.get("audio_file_id"),
            audio_url=task.get("audio_url"),
            audio_sha256=task.get("audio_sha256"),
        )
        return {"success": response.success, "task": audio_review_service.get_task(task_id), "result": response.result}




    def _processing_result(
        self,
        *,
        task_id: str,
        filename: str,
        audio_file_id: str | None,
        audio_url: str | None,
        audio_sha256: str | None,
        baidu_task_id: str,
        raw_result: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "agent": self.name,
            "task_type": self.task_type,
            "success": True,
            "status": "transcribing",
            "task_id": task_id,
            "message": "百度音频文件转写仍在处理中，请稍后刷新。本系统不会用空转写生成 0 分报告。",
            "summary": {
                "overall_score": None,
                "accuracy_score": None,
                "expression_score": None,
                "project_depth_score": None,
                "completeness_score": None,
                "logic_score": None,
                "strengths": [],
                "main_problems": [],
                "main_suggestions": [],
                "next_steps": [],
                "review_focus": ["等待百度返回转写文本", "转写完成后再进行题目切分和答案评估"],
                "question_scores": [],
            },
            "transcript": {"raw_text": "", "speaker_mapping": {}, "segments": []},
            "qa_pairs": [],
            "qa_analysis": [],
            "review_status": "transcribing",
            "review_logs": audio_review_service.logs(task_id),
            "raw_baidu_result": raw_result,
            "metadata": {
                "audio_filename": filename,
                "audio_file_id": audio_file_id,
                "audio_url": audio_url,
                "audio_sha256": audio_sha256,
                "baidu_task_id": baidu_task_id,
                "used_baidu_asr": True,
                "used_speaker_diarization": False,
                "used_lightrag": False,
                "used_baidu_ai_search": False,
                "used_deepseek": False,
            },
        }













    def _error(self, code: str, message: str) -> AgentResponse:
        return AgentResponse(
            success=False,
            agent=self.name,
            task_type=self.task_type,
            message=message,
            result={"success": False, "error": code, "message": message},
        )
