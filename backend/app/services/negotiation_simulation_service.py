from __future__ import annotations

import logging
from typing import Any

from app.services.salary_paths import env_bool, salary_rl_model_path

logger = logging.getLogger(__name__)


class NegotiationSimulationService:
    def __init__(self) -> None:
        self._rl_checked = False
        self._rl_available = False
        self._rl_error = ""

    def status(self) -> dict[str, Any]:
        self._check_rl()
        return {
            "rl_available": self._rl_available,
            "rl_model_path": str(salary_rl_model_path()),
            "message": "PPO 强化学习模拟已启用。" if self._rl_available else self._rl_error,
        }

    def simulate(self, market_salary: float, exp_level: int = 1, company_size: int = 1) -> dict[str, Any]:
        self._check_rl()
        if self._rl_available:
            # The reference PPO model is optional and not bundled in the current
            # demo copy. Keep the interface ready; the rule fallback below keeps
            # the workbench usable while clearly marking non-RL mode.
            pass

        return self._fallback_simulation(market_salary, exp_level, company_size)

    def _check_rl(self) -> None:
        if self._rl_checked:
            return
        self._rl_checked = True
        if not env_bool("SALARY_ENABLE_RL_SIMULATION", True):
            self._rl_error = "强化学习模拟暂不可用：SALARY_ENABLE_RL_SIMULATION=false。"
            return
        path = salary_rl_model_path()
        if not path.exists() and not path.with_suffix(".zip").exists():
            self._rl_error = "强化学习模拟暂不可用：未找到 PPO 模型文件。"
            return
        try:
            import stable_baselines3  # noqa: F401  # type: ignore

            self._rl_available = True
            self._rl_error = ""
        except Exception as exc:  # pragma: no cover - optional dependency path
            logger.warning("salary RL dependencies unavailable: %s", exc)
            self._rl_error = f"强化学习模拟暂不可用：{exc}"

    def _fallback_simulation(self, market_salary: float, exp_level: int, company_size: int) -> dict[str, Any]:
        market_salary = float(market_salary or 119000)
        leverage = 1 + max(0, exp_level) * 0.045 + max(0, company_size) * 0.025
        candidate = market_salary * (1.18 + exp_level * 0.025)
        hr = market_salary * (0.92 + company_size * 0.035)
        rounds = []
        action_names = ["坚持报价", "小幅退让 (-3%)", "强调市场证据"]
        advice = [
            "先用预测区间和技能稀缺性锚定高位报价。",
            "如果 HR 强调预算，可以小幅退让但保留签字费或绩效空间。",
            "补充行业趋势和同类岗位基准，要求 HR 给出可量化调整方案。",
        ]
        for index in range(4):
            candidate *= 0.985 if index else 1
            hr *= 1.035
            done = index == 3 or abs(candidate - hr) / market_salary < 0.08
            final = round((candidate * 0.47 + hr * 0.53) / 1000) * 1000 if done else 0
            rounds.append(
                {
                    "round": index + 1,
                    "action": action_names[min(index, 2)],
                    "advice": advice[min(index, 2)],
                    "candidate_offer": round(candidate),
                    "hr_offer": round(hr),
                    "final_salary": final,
                    "done": done,
                    "hr_feedback": "预算需要审批，但可讨论总包结构。" if not done else "如果能本周确认入职，HR 可以推动该方案。",
                }
            )
            if done:
                break

        final_salary = int(rounds[-1]["final_salary"] or market_salary * leverage)
        vs_market = round((final_salary / market_salary - 1) * 100, 1)
        return {
            "success": True,
            "rl_available": False,
            "status": "fallback",
            "message": self._rl_error or "强化学习模拟暂不可用，当前为规则降级模拟。",
            "rounds": rounds,
            "final_salary": final_salary,
            "market_salary": round(market_salary),
            "vs_market": vs_market,
            "hr_budget": round(market_salary * (1.08 + company_size * 0.03)),
            "result_text": f"规则模拟成交价约 ${final_salary:,}，相对市场基准 {'+' if vs_market >= 0 else ''}{vs_market}%。",
        }


negotiation_simulation_service = NegotiationSimulationService()
