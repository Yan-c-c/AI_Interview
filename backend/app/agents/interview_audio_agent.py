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

    async def _complete_analysis(
        self,
        *,
        request: AgentRequest,
        task_id: str,
        transcript: dict[str, Any],
        filename: str,
        audio_file_id: str | None,
        audio_url: str | None,
        audio_sha256: str | None = None,
        text_transcript: bool = False,
    ) -> AgentResponse:
        if not transcript.get("raw_text") and not transcript.get("segments"):
            failed = audio_review_service.fail_task(task_id, "百度任务已返回，但没有可解析的转写文本。")
            return AgentResponse(
                success=False,
                agent=self.name,
                task_type=self.task_type,
                message="百度任务已返回，但没有可解析的转写文本。",
                result={"success": False, "task_id": task_id, "status": "transcription_empty", "task": failed},
            )

        speaker_mapping = await self._identify_speakers(request, transcript)
        qa_pairs = await self._split_qa_pairs(request, transcript, speaker_mapping)
        qa_analysis = []
        used_lightrag = False
        used_baidu_ai_search = False
        for qa in qa_pairs:
            evidence = await public_answer_search_service.search(qa.get("question") or "")
            used_lightrag = used_lightrag or evidence["source_status"] == "lightrag_hit"
            used_baidu_ai_search = used_baidu_ai_search or evidence["source_status"] == "baidu_ai_search_hit"
            qa_analysis.append(await self._judge_answer(request, qa, evidence))

        summary = await self._summarize_report(request, qa_analysis)
        result = {
            "agent": self.name,
            "task_type": self.task_type,
            "success": True,
            "task_id": task_id,
            "summary": summary,
            "transcript": {
                "raw_text": transcript.get("raw_text") or "",
                "speaker_mapping": speaker_mapping,
                "segments": self._apply_speaker_roles(transcript.get("segments") or [], speaker_mapping),
            },
            "qa_pairs": qa_pairs,
            "qa_analysis": qa_analysis,
            "review_status": "completed" if text_transcript else "pending_review",
            "review_logs": audio_review_service.logs(task_id),
            "metadata": {
                "audio_filename": filename,
                "audio_file_id": audio_file_id,
                "audio_url": audio_url,
                "audio_sha256": audio_sha256,
                "baidu_task_id": transcript.get("baidu_task_id"),
                "used_baidu_asr": not text_transcript,
                "used_text_transcript": text_transcript,
                "used_speaker_diarization": not text_transcript,
                "used_lightrag": used_lightrag,
                "used_baidu_ai_search": used_baidu_ai_search,
                "used_deepseek": True,
            },
        }
        task = audio_review_service.update_result(task_id, result)
        result["review_logs"] = audio_review_service.logs(task_id)
        return AgentResponse(
            success=True,
            agent=self.name,
            task_type=self.task_type,
            message="面试对话文本分析已完成。" if text_transcript else "面试录音分析已完成，等待讲师审核。",
            result={"success": True, "task_id": task_id, "task": task, **result},
        )

    def _transcript_from_text(self, transcript_text: str) -> dict[str, Any]:
        segments: list[dict[str, Any]] = []
        lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]
        if not lines:
            lines = [transcript_text.strip()]
        for index, line in enumerate(lines):
            speaker, text = self._parse_text_speaker(line, index)
            segments.append(
                {
                    "speaker": speaker,
                    "text": text,
                    "start_time": f"00:{index:02d}",
                    "end_time": f"00:{index + 1:02d}",
                }
            )
        return {
            "raw_text": transcript_text,
            "segments": segments,
            "baidu_task_id": "",
            "raw_result": {},
        }

    def _parse_text_speaker(self, line: str, index: int) -> tuple[str, str]:
        match = re.match(r"^\s*([^:：]{1,16})\s*[:：]\s*(.+)$", line)
        if match:
            label = match.group(1).strip().lower()
            text = match.group(2).strip()
            interviewer_labels = {"面试官", "hr", "interviewer", "问", "q", "老师", "招聘方"}
            candidate_labels = {"候选人", "面试者", "candidate", "答", "a", "我", "学生", "求职者"}
            if label in interviewer_labels:
                return "speaker_0", text
            if label in candidate_labels:
                return "speaker_1", text
            return "speaker_0" if any(token in label for token in interviewer_labels) else "speaker_1", text
        return ("speaker_0" if ("?" in line or "？" in line or index % 2 == 0) else "speaker_1", line)

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

    async def _identify_speakers(self, request: AgentRequest, transcript: dict[str, Any]) -> dict[str, str]:
        segments = transcript.get("segments") or []
        speakers = sorted({str(item.get("speaker") or "") for item in segments if item.get("speaker")})
        if not speakers:
            return {}
        fallback = {speaker: ("interviewer" if index == 0 else "candidate") for index, speaker in enumerate(speakers)}
        try:
            llm = get_llm_for_request(request.api_config, channel="smart", temperature=0.1, max_tokens=1200)
            sample = "\n".join(f"{item.get('speaker')}: {item.get('text')}" for item in segments[:80])
            response = await llm.ainvoke(
                [
                    SystemMessage(content="你是面试录音话者角色识别 Agent。只输出 JSON，不要 markdown。"),
                    HumanMessage(
                        content=f"""根据下列转写片段判断每个 speaker 是面试官 interviewer 还是面试者 candidate。
面试官通常负责提问、追问、引导；面试者通常负责回答、解释项目、说明方案。

转写片段：
{sample}

输出格式：
{{"speaker_mapping": {{"speaker_0": "interviewer", "speaker_1": "candidate"}}}}"""
                    ),
                ]
            )
            data = loads_json_response(str(response.content or ""))
            mapping = data.get("speaker_mapping") if isinstance(data, dict) else None
            if isinstance(mapping, dict):
                normalized = {speaker: str(mapping.get(speaker) or fallback.get(speaker) or "candidate") for speaker in speakers}
                for speaker, role in normalized.items():
                    if role not in {"interviewer", "candidate"}:
                        normalized[speaker] = fallback.get(speaker, "candidate")
                return normalized
        except Exception as exc:
            logger.warning("speaker mapping failed: %s", exc)
        return fallback

    async def _split_qa_pairs(self, request: AgentRequest, transcript: dict[str, Any], speaker_mapping: dict[str, str]) -> list[dict[str, Any]]:
        segments = self._apply_speaker_roles(transcript.get("segments") or [], speaker_mapping)
        fallback = self._fallback_split_qa(segments)
        try:
            llm = get_llm_for_request(request.api_config, channel="smart", temperature=0.1, max_tokens=4200)
            compact = "\n".join(f"{item.get('start_time')} {item.get('role')} {item.get('text')}" for item in segments[:160])
            response = await llm.ainvoke(
                [
                    SystemMessage(content="你是面试录音问答切分 Agent。只输出 JSON，不要 markdown。"),
                    HumanMessage(
                        content=f"""请把面试转写切分为“面试官问题 + 面试者回答”的结构化问答对。
要求保留开始和结束时间，问题要尽量合并追问上下文，回答只包含面试者内容。

转写：
{compact}

输出 JSON：
{{"qa_pairs": [
  {{"question_id": "q1", "question": "", "answer": "", "interviewer_segments": [], "candidate_segments": [], "start_time": "00:00", "end_time": "00:00"}}
]}}"""
                    ),
                ]
            )
            data = loads_json_response(str(response.content or ""))
            qa_pairs = data.get("qa_pairs") if isinstance(data, dict) else None
            if isinstance(qa_pairs, list) and qa_pairs:
                return [self._normalize_qa(item, index) for index, item in enumerate(qa_pairs, start=1) if isinstance(item, dict)]
        except Exception as exc:
            logger.warning("qa split failed: %s", exc)
        return fallback

    async def _judge_answer(self, request: AgentRequest, qa: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
        lightrag = evidence.get("lightrag")
        baidu = evidence.get("baidu_ai_search")
        source_status = evidence.get("source_status")
        evidence_sources = list(evidence.get("evidence_sources") or [])
        if not evidence_sources:
            evidence_sources = [{"source_type": "deepseek_generated", "title": "DeepSeek 兜底生成", "url": "", "summary": "未检索到可靠题库或公开网页来源。"}]
        try:
            llm = get_llm_for_request(request.api_config, channel="smart", temperature=0.15, max_tokens=3600)
            response = await llm.ainvoke(
                [
                    SystemMessage(content="你是技术面试答案评估专家。必须结合证据判断，不要只做关键词匹配。只输出 JSON。"),
                    HumanMessage(
                        content=f"""面试题：
{qa.get('question')}

学生回答：
{qa.get('answer')}

本地面试知识库检索：
{getattr(lightrag, 'response', '') if lightrag else ''}
{getattr(lightrag, 'references', []) if lightrag else []}

百度 AI 搜索结果：
{baidu.answer if baidu else ''}
{baidu.sources if baidu else []}

检索状态：{source_status}

请生成该题的标准答案和准确性评估。若无可靠证据，必须说明来源为 deepseek_generated，不要编造 URL。
输出 JSON：
{{
  "question": "",
  "candidate_answer": "",
  "standard_answer": "",
  "accuracy_score": 85,
  "accuracy_level": "基本准确",
  "correct_points": [],
  "missing_points": [],
  "wrong_points": [],
  "knowledge_points": [],
  "evidence_sources": [],
  "feedback": "",
  "improvement_suggestion": ""
}}"""
                    ),
                ]
            )
            data = loads_json_response(str(response.content or ""))
            if isinstance(data, dict):
                data.setdefault("question_id", qa.get("question_id"))
                data.setdefault("question", qa.get("question"))
                data.setdefault("candidate_answer", qa.get("answer"))
                data["accuracy_score"] = self._score(data.get("accuracy_score"), default=70)
                data["evidence_sources"] = self._normalize_sources(data.get("evidence_sources") or evidence_sources, evidence_sources)
                return data
        except Exception as exc:
            logger.warning("answer judge failed: %s", exc)
        return self._fallback_judge(qa, evidence_sources)

    async def _summarize_report(self, request: AgentRequest, qa_analysis: list[dict[str, Any]]) -> dict[str, Any]:
        fallback = self._fallback_summary(qa_analysis)
        try:
            llm = get_llm_for_request(request.api_config, channel="smart", temperature=0.15, max_tokens=2400)
            response = await llm.ainvoke(
                [
                    SystemMessage(content="你是面试录音评估报告生成 Agent。只输出 JSON。"),
                    HumanMessage(
                        content=f"""根据逐题评估生成面试录音分析总报告：
{qa_analysis}

输出 JSON：
{{
  "overall_score": 82,
  "accuracy_score": 78,
  "expression_score": 85,
  "project_depth_score": 80,
  "completeness_score": 80,
  "logic_score": 82,
  "strengths": [],
  "main_problems": [],
  "question_scores": [],
  "review_focus": [],
  "main_suggestions": [],
  "next_steps": []
}}"""
                    ),
                ]
            )
            data = loads_json_response(str(response.content or ""))
            if isinstance(data, dict):
                return {**fallback, **data}
        except Exception as exc:
            logger.warning("audio report summary failed: %s", exc)
        return fallback

    def _apply_speaker_roles(self, segments: list[dict[str, Any]], mapping: dict[str, str]) -> list[dict[str, Any]]:
        normalized = []
        for item in segments:
            speaker = str(item.get("speaker") or "")
            normalized.append({**item, "role": mapping.get(speaker, "candidate")})
        return normalized

    def _fallback_split_qa(self, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pairs: list[dict[str, Any]] = []
        current_question: list[dict[str, Any]] = []
        current_answer: list[dict[str, Any]] = []
        for item in segments:
            if item.get("role") == "interviewer":
                if current_question and current_answer:
                    pairs.append(self._qa_from_segments(len(pairs) + 1, current_question, current_answer))
                    current_question = []
                    current_answer = []
                current_question.append(item)
            else:
                if current_question:
                    current_answer.append(item)
        if current_question:
            pairs.append(self._qa_from_segments(len(pairs) + 1, current_question, current_answer))
        return pairs

    def _qa_from_segments(self, index: int, questions: list[dict[str, Any]], answers: list[dict[str, Any]]) -> dict[str, Any]:
        all_segments = [*questions, *answers]
        return {
            "question_id": f"q{index}",
            "question": " ".join(str(item.get("text") or "") for item in questions).strip(),
            "answer": " ".join(str(item.get("text") or "") for item in answers).strip(),
            "interviewer_segments": questions,
            "candidate_segments": answers,
            "start_time": all_segments[0].get("start_time") if all_segments else "00:00",
            "end_time": all_segments[-1].get("end_time") if all_segments else "00:00",
        }

    def _normalize_qa(self, item: dict[str, Any], index: int) -> dict[str, Any]:
        return {
            "question_id": str(item.get("question_id") or f"q{index}"),
            "question": str(item.get("question") or "").strip(),
            "answer": str(item.get("answer") or "").strip(),
            "interviewer_segments": item.get("interviewer_segments") if isinstance(item.get("interviewer_segments"), list) else [],
            "candidate_segments": item.get("candidate_segments") if isinstance(item.get("candidate_segments"), list) else [],
            "start_time": str(item.get("start_time") or "00:00"),
            "end_time": str(item.get("end_time") or "00:00"),
        }

    def _fallback_judge(self, qa: dict[str, Any], evidence_sources: list[dict[str, str]]) -> dict[str, Any]:
        score = 65 if qa.get("answer") else 20
        return {
            "question_id": qa.get("question_id"),
            "question": qa.get("question") or "",
            "candidate_answer": qa.get("answer") or "",
            "standard_answer": "当前未能完成完整证据综合，请讲师结合题库和候选人回答进一步审核。",
            "accuracy_score": score,
            "accuracy_level": "待人工复核" if score >= 60 else "回答不足",
            "correct_points": [],
            "missing_points": ["需要补充标准答案中的关键概念、适用场景和项目落地细节。"],
            "wrong_points": [],
            "knowledge_points": [],
            "evidence_sources": evidence_sources,
            "feedback": "AI 评估链路未完整完成，建议优先人工复核。",
            "improvement_suggestion": "围绕问题核心概念、项目中的具体做法和结果进行结构化回答。",
        }

    def _fallback_summary(self, qa_analysis: list[dict[str, Any]]) -> dict[str, Any]:
        scores = [self._score(item.get("accuracy_score"), default=60) for item in qa_analysis]
        avg = round(sum(scores) / len(scores)) if scores else 0
        return {
            "overall_score": avg,
            "accuracy_score": avg,
            "expression_score": avg,
            "project_depth_score": avg,
            "completeness_score": avg,
            "logic_score": avg,
            "strengths": [],
            "main_problems": ["部分问题仍需讲师复核标准答案和评分依据。"],
            "question_scores": [{"question_id": item.get("question_id"), "score": item.get("accuracy_score")} for item in qa_analysis],
            "review_focus": ["核对转写是否准确", "核对题目切分是否完整", "确认标准答案是否适合入库"],
            "main_suggestions": ["优先修正低分问题的标准答案和知识点标签。"],
            "next_steps": ["讲师审核通过后收录到面试知识库。"],
        }

    def _normalize_sources(self, value: Any, fallback: list[dict[str, str]]) -> list[dict[str, str]]:
        if not isinstance(value, list) or not value:
            return fallback
        sources = []
        for item in value:
            if not isinstance(item, dict):
                continue
            source_type = str(item.get("source_type") or "deepseek_generated")
            if source_type not in {"lightrag", "baidu_ai_search", "deepseek_generated"}:
                source_type = "deepseek_generated"
            sources.append(
                {
                    "source_type": source_type,
                    "title": str(item.get("title") or ""),
                    "url": str(item.get("url") or ""),
                    "summary": str(item.get("summary") or "")[:700],
                }
            )
        return sources or fallback

    def _score(self, value: Any, *, default: int) -> int:
        try:
            return max(0, min(100, int(float(value))))
        except (TypeError, ValueError):
            return default

    def _error(self, code: str, message: str) -> AgentResponse:
        return AgentResponse(
            success=False,
            agent=self.name,
            task_type=self.task_type,
            message=message,
            result={"success": False, "error": code, "message": message},
        )
