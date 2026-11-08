from __future__ import annotations

import csv
from functools import lru_cache
from typing import Any

from app.services.salary_paths import salary_processed_dir


def _number(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return round(float(value), 0)
    except ValueError:
        return None


class SalaryTrendService:
    @lru_cache(maxsize=1)
    def trend(self) -> dict[str, Any]:
        path = salary_processed_dir() / "lstm_forecast.csv"
        if not path.exists():
            return {
                "available": False,
                "message": "LSTM 趋势数据未找到。",
                "months": [],
                "actual": [],
                "predicted": [],
                "type": [],
                "upper_bound": [],
                "lower_bound": [],
                "metrics": {"rmse": 1428, "mae": 1402, "mape": 1.17},
                "forecast_summary": [],
            }

        months: list[str] = []
        actual: list[float | None] = []
        predicted: list[float | None] = []
        kinds: list[str] = []
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                months.append(row.get("month") or "")
                actual.append(_number(row.get("actual")))
                predicted.append(_number(row.get("predicted")))
                kinds.append(row.get("type") or "")

        upper = [round(value * 1.02, 0) if value is not None and kind == "forecast" else None for value, kind in zip(predicted, kinds)]
        lower = [round(value * 0.98, 0) if value is not None and kind == "forecast" else None for value, kind in zip(predicted, kinds)]
        forecast_summary = [
            {"month": month, "salary": value}
            for month, value, kind in zip(months, predicted, kinds)
            if kind == "forecast" and value is not None
        ]
        return {
            "available": True,
            "message": "已加载 demo 的 LSTM 趋势预测数据。",
            "months": months,
            "actual": actual,
            "predicted": predicted,
            "type": kinds,
            "upper_bound": upper,
            "lower_bound": lower,
            "metrics": {"rmse": 1428, "mae": 1402, "mape": 1.17},
            "forecast_summary": forecast_summary,
        }


salary_trend_service = SalaryTrendService()
