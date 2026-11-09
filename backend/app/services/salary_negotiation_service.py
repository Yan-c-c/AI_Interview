from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.json_utils import loads_json_response
from app.core.llms import get_llm_for_request
from app.schemas.agent_schema import AgentRequest
from app.services.negotiation_simulation_service import negotiation_simulation_service
from app.services.salary_benchmark_service import salary_benchmark_service
from app.services.salary_prediction_service import salary_prediction_service
from app.services.salary_trend_service import salary_trend_service

logger = logging.getLogger(__name__)


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.replace("，", ",").replace("、", ",").split(",") if item.strip()]
    return []


class SalaryNegotiationService:
    def __init__(self) -> None:
        self.history_dir = Path(__file__).resolve().parents[2] / "data" / "salary_negotiations"
        self.history_dir.mkdir(parents=True, exist_ok=True)

    async def analyze(self, request: AgentRequest) -> dict[str, Any]:
        profile = self._profile_from_request(request)
        prediction = salary_prediction_service.predict(profile)
        trend = salary_trend_service.trend()
        benchmarks = salary_benchmark_service.market_overview()
        explain = prediction.get("explanation") or {}
        simulation = negotiation_simulation_service.simulate(
            market_salary=prediction.get("salary_raw") or salary_benchmark_service.heuristic_salary(profile),
            exp_level=self._exp_to_int(profile.get("experience_level")),
            company_size=self._size_to_int(profile.get("company_size")),
        )
        strategy = await self.generate_strategy(
            profile=profile,
            prediction=prediction,
            trend=trend,
            simulation=simulation,
            api_config=request.api_config,
            message=request.message,
        )
        report = {
            "agent": "salary_negotiation_agent",
            "task_type": "salary_negotiation",
            "success": True,
            "profile": profile,
            "prediction": prediction,
            "trend": trend,
            "benchmarks": benchmarks,
            "explainability": explain,
            "simulation": simulation,
            "strategy": strategy,
            "metadata": {
                "history_id": str(uuid.uuid4()),
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "used_demo_salary_data": True,
                "used_local_salary_model": bool(prediction.get("model_available")),
                "used_rl_simulation": bool(simulation.get("rl_available")),
                "used_deepseek": bool(strategy.get("used_deepseek")),
                "degradation_notes": [
                    item
                    for item in [
                        None if prediction.get("model_available") else prediction.get("message"),
                        None if simulation.get("rl_available") else simulation.get("message"),
                    ]
                    if item
                ],
            },
        }
        self._save_history(report)
        return report

    async def generate_strategy(
        self,
        *,
        profile: dict[str, Any],
        prediction: dict[str, Any],
        trend: dict[str, Any],
        simulation: dict[str, Any],
        api_config: dict[str, Any] | None = None,
        message: str = "",
    ) -> dict[str, Any]:
        try:
            llm = get_llm_for_request(api_config, channel="smart", temperature=0.25, max_tokens=4200)
            response = await llm.ainvoke(
                [
                    SystemMessage(
                        content=(
                            "你是薪资谈判 Agent。结合用户画像、薪资预测、趋势数据和谈判模拟，"
                            "输出可执行的谈薪策略。必须只输出 JSON，不要编造模型来源。"
                        )
                    ),
                    HumanMessage(
                        content=f"""用户需求：
{message}

用户画像：
{json.dumps(profile, ensure_ascii=False)}

薪资预测：
{json.dumps(prediction, ensure_ascii=False)}

趋势分析：
{json.dumps(trend, ensure_ascii=False)[:6000]}

谈判模拟：
{json.dumps(simulation, ensure_ascii=False)}

请输出 JSON：
{{
  "reasonable_range": "",
  "target_salary": 0,
  "minimum_acceptable_salary": 0,
  "offer_decision": "",
  "negotiation_strategy": [],
  "talking_scripts": [],
  "hr_pushback_responses": [],
  "risk_alerts": [],
  "final_report": "",
  "used_deepseek": true
}}"""
                    ),
                ]
            )
            data = loads_json_response(str(response.content or ""))
            if not isinstance(data, dict):
                raise ValueError("strategy response is not object")
            data["used_deepseek"] = True
            return self._normalize_strategy(data, prediction)
        except Exception as exc:
            logger.warning("salary strategy generation failed: %s", exc)
            fallback = self._fallback_strategy(profile, prediction, simulation)
            fallback["used_deepseek"] = False
            fallback["llm_error"] = str(exc)
            return fallback

    def simulate(self, market_salary: float, exp_level: int, company_size: int) -> dict[str, Any]:
        return negotiation_simulation_service.simulate(market_salary, exp_level, company_size)

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self.history_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
            try:
                items.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return items

    def _profile_from_request(self, request: AgentRequest) -> dict[str, Any]:
        metadata = request.metadata or {}
        message = request.message or ""
        skills = metadata.get("skills") or []
        if not skills:
            skills = _list(metadata.get("skills_text") or self._extract_text_field(message, ["技能栈", "技能", "技术栈"]))
        years = metadata.get("years_experience")
        if years is None:
            years = self._extract_years(message)
        city = str(metadata.get("city") or self._extract_text_field(message, ["城市", "地点", "base"]) or "").strip()
        return {
            "job_title": str(metadata.get("job_title") or self._extract_text_field(message, ["岗位", "职位", "目标岗位"]) or "AI Engineer").strip(),
            "experience_level": str(metadata.get("experience_level") or "MI").upper().strip(),
            "years_experience": int(years or 3),
            "country": str(metadata.get("country") or ("CHINA" if city else "UNITED STATES")).upper().strip(),
            "city": city,
            "company_size": str(metadata.get("company_size") or "M").upper().strip(),
            "industry": str(metadata.get("industry") or "Technology").strip(),
            "employment_type": str(metadata.get("employment_type") or "FT").upper().strip(),
            "remote_ratio": int(metadata.get("remote_ratio") or 50),
            "education_required": str(metadata.get("education_required") or "Bachelor").strip(),
            "skills": skills if isinstance(skills, list) else _list(skills),
            "current_offer": metadata.get("current_offer") or self._extract_salary(message, ["offer", "报价", "当前薪资", "当前"]),
            "expected_salary": metadata.get("expected_salary") or self._extract_salary(message, ["期望薪资", "期望", "目标薪资"]),
            "resume_text_available": bool((request.resume_text or "").strip()),
        }

    def _extract_text_field(self, text: str, labels: list[str]) -> str:
        for label in labels:
            match = re.search(rf"{label}\s*[:：]\s*([^\n，,。；;]+)", text, flags=re.I)
            if match:
                return match.group(1).strip()[:80]
        return ""

    def _extract_years(self, text: str) -> int | None:
        match = re.search(r"(\d{1,2})\s*年(?:工作|相关|项目|经验)?", text)
        if not match:
            return None
        return max(0, min(40, int(match.group(1))))

    def _extract_salary(self, text: str, labels: list[str]) -> str:
        for label in labels:
            match = re.search(rf"{label}[^0-9\n]{{0,12}}([\d.]+)\s*([kK]|w|W|万|千|元|人民币|rmb|RMB)?", text, flags=re.I)
            if match:
                return f"{match.group(1)}{match.group(2) or ''}".strip()
        return ""

    def _normalize_strategy(self, data: dict[str, Any], prediction: dict[str, Any]) -> dict[str, Any]:
        salary = int(prediction.get("salary_raw") or 100000)
        return {
            "reasonable_range": str(data.get("reasonable_range") or f"{prediction.get('salary_low')} - {prediction.get('salary_high')}"),
            "target_salary": int(data.get("target_salary") or round(salary * 1.08)),
            "minimum_acceptable_salary": int(data.get("minimum_acceptable_salary") or round(salary * 0.92)),
            "offer_decision": str(data.get("offer_decision") or "建议结合预测区间和个人优先级再决定。"),
            "negotiation_strategy": _list(data.get("negotiation_strategy"))[:8],
            "talking_scripts": _list(data.get("talking_scripts"))[:8],
            "hr_pushback_responses": _list(data.get("hr_pushback_responses"))[:8],
            "risk_alerts": _list(data.get("risk_alerts"))[:8],
            "final_report": str(data.get("final_report") or "建议围绕市场基准、项目贡献和替代方案开展谈薪。"),
            "used_deepseek": bool(data.get("used_deepseek")),
        }

    def _fallback_strategy(self, profile: dict[str, Any], prediction: dict[str, Any], simulation: dict[str, Any]) -> dict[str, Any]:
        salary = int(prediction.get("salary_raw") or 100000)
        high = int(prediction.get("salary_high_raw") or salary * 1.17)
        low = int(prediction.get("salary_low_raw") or salary * 0.83)
        return self._normalize_strategy(
            {
                "reasonable_range": f"${low:,} - ${high:,}",
                "target_salary": round(high * 0.96),
                "minimum_acceptable_salary": round(salary * 0.9),
                "offer_decision": "如果当前 offer 低于预测下限，建议继续谈；如果位于预测区间中上部，可重点争取签字费、绩效和远程条件。",
                "negotiation_strategy": [
                    "先用市场预测区间建立锚点，不要直接接受首轮报价。",
                    "突出与岗位强相关的项目、技能稀缺性和可立即交付价值。",
                    "若 HR 压预算，优先谈总包结构：签字费、绩效、调薪窗口和远程比例。",
                ],
                "talking_scripts": [
                    f"结合我的经验和岗位职责，我看到该岗位合理区间约为 ${low:,} - ${high:,}，我更希望目标总包靠近 ${round(high * 0.96):,}。",
                    "我能在入职后直接承担核心模块交付，因此希望薪资能体现岗位匹配度和交付风险降低。",
                ],
                "hr_pushback_responses": [
                    "如果固定薪资受限，是否可以通过签字费、季度绩效或 6 个月调薪评审补足差距？",
                    "我理解预算边界，也希望我们基于岗位市场价和职责范围找到双方都能接受的方案。",
                ],
                "risk_alerts": [
                    "不要在第一轮就暴露最低可接受薪资。",
                    "不要只说“我觉得应该更高”，要带预测区间、竞品 offer 或具体贡献证据。",
                    simulation.get("message") or "",
                ],
                "final_report": "当前策略为规则降级生成，可在 DeepSeek 配置可用后生成更个性化话术。",
            },
            prediction,
        )

    def _exp_to_int(self, value: Any) -> int:
        return {"EN": 0, "MI": 1, "SE": 2, "EX": 3}.get(str(value or "MI").upper(), 1)

    def _size_to_int(self, value: Any) -> int:
        return {"S": 0, "M": 1, "L": 2}.get(str(value or "M").upper(), 1)

    def _save_history(self, report: dict[str, Any]) -> None:
        history_id = report.get("metadata", {}).get("history_id") or str(uuid.uuid4())
        path = self.history_dir / f"{history_id}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


salary_negotiation_service = SalaryNegotiationService()
