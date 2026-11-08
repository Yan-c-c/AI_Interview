from __future__ import annotations

import logging
from typing import Any

from app.services.salary_benchmark_service import salary_benchmark_service
from app.services.salary_explain_service import salary_explain_service
from app.services.salary_paths import salary_model_path, salary_word2vec_model_path

logger = logging.getLogger(__name__)


class SalaryPredictionService:
    def __init__(self) -> None:
        self._model: Any = None
        self._model_checked = False
        self._model_error = ""

    def predict(self, profile: dict[str, Any]) -> dict[str, Any]:
        model_result = self._predict_with_model(profile)
        if model_result:
            salary = int(model_result["salary_raw"])
            source = "xgboost_model"
            model_available = True
            model_message = "已使用 demo XGBoost 模型预测。"
        else:
            salary = salary_benchmark_service.heuristic_salary(profile)
            source = "heuristic_benchmark"
            model_available = False
            model_message = self._model_error or "本地薪资预测模型暂不可用，已使用 demo 市场基准和规则特征降级估算。"

        low = int(round(salary * 0.83 / 1000) * 1000)
        high = int(round(salary * 1.17 / 1000) * 1000)
        offer = profile.get("current_offer")
        offer_gap = None
        if offer:
            try:
                offer_gap = round((float(offer) / salary - 1) * 100, 1)
            except (TypeError, ValueError, ZeroDivisionError):
                offer_gap = None

        explanation = salary_explain_service.explain_prediction(profile, salary)
        return {
            "available": True,
            "model_available": model_available,
            "source": source,
            "message": model_message,
            "salary": f"${salary:,}",
            "salary_raw": salary,
            "salary_low": f"${low:,}",
            "salary_high": f"${high:,}",
            "salary_low_raw": low,
            "salary_high_raw": high,
            "confidence_interval": [low, high],
            "offer_gap_percent": offer_gap,
            "skill_note": self._skill_note(profile),
            "model_paths": {
                "salary_model_path": str(salary_model_path()),
                "word2vec_model_path": str(salary_word2vec_model_path()),
            },
            "explanation": explanation,
        }

    def _predict_with_model(self, profile: dict[str, Any]) -> dict[str, Any] | None:
        # The reference demo ships trained-code paths, but the current copy may
        # not include binary model artifacts or heavy ML deps. Keep this lazy and
        # isolated so the Agent can degrade without breaking the app.
        if not self._model_checked:
            self._model_checked = True
            model_path = salary_model_path()
            if not model_path.exists():
                self._model_error = "本地薪资预测模型暂不可用：未找到 XGBoost 模型文件。"
                return None
            try:
                import joblib  # type: ignore

                self._model = joblib.load(model_path)
            except Exception as exc:  # pragma: no cover - optional dependency path
                logger.warning("salary model load failed: %s", exc)
                self._model_error = f"本地薪资预测模型暂不可用：{exc}"
                self._model = None

        if self._model is None:
            return None
        # A full 153-dim feature build requires the original training stack. The
        # model artifact is optional here; until present, heuristic fallback is
        # safer than silently producing malformed predictions.
        self._model_error = "本地薪资预测模型已发现，但当前服务未加载完整 153 维特征工程管线，已降级估算。"
        return None

    def _skill_note(self, profile: dict[str, Any]) -> list[str]:
        skills = profile.get("skills") or []
        if isinstance(skills, str):
            skills = [item.strip() for item in skills.split(",") if item.strip()]
        if not skills:
            return ["info", "未输入技能。补充技能栈后，DeepSeek 策略会更准确。"]
        return ["ok", f"已纳入 {len(skills)} 个技能：{', '.join(map(str, skills[:8]))}。"]


salary_prediction_service = SalaryPredictionService()
