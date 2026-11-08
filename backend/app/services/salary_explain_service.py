from __future__ import annotations

import csv
from functools import lru_cache
from typing import Any

from app.services.salary_paths import salary_processed_dir


FEATURE_CN = {
    "Years of Experience": "工作年限",
    "Company Size": "公司规模",
    "Experience Level": "经验等级",
    "Country: India": "国家：印度",
    "Country: China": "国家：中国",
    "Country: Switzerland": "国家：瑞士",
    "Country: Denmark": "国家：丹麦",
    "Country: Norway": "国家：挪威",
    "Country: United States": "国家：美国",
}


class SalaryExplainService:
    @lru_cache(maxsize=1)
    def feature_importance(self) -> list[dict[str, Any]]:
        path = salary_processed_dir() / "shap_importance.csv"
        if not path.exists():
            return [
                {"feature": "工作年限", "feature_raw": "years_experience", "importance": 0.28},
                {"feature": "公司规模", "feature_raw": "size_encoded", "importance": 0.08},
                {"feature": "经验等级", "feature_raw": "exp_level_encoded", "importance": 0.07},
            ]
        items: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                name = row.get("feature") or ""
                try:
                    importance = float(row.get("importance") or 0)
                except ValueError:
                    importance = 0
                items.append(
                    {
                        "feature": FEATURE_CN.get(name, name),
                        "feature_raw": row.get("feature_raw") or "",
                        "importance": round(importance, 4),
                    }
                )
        return items

    def explain_prediction(self, profile: dict[str, Any], salary: int) -> dict[str, Any]:
        base = self.feature_importance()[:8]
        years = int(profile.get("years_experience") or 0)
        exp = str(profile.get("experience_level") or "MI")
        country = str(profile.get("country") or "UNITED STATES")
        skills = profile.get("skills") if isinstance(profile.get("skills"), list) else []
        narrative = [
            f"模型解释显示，工作年限、经验等级和所在国家是薪资预测的主要驱动因素。",
            f"当前画像为 {exp} 等级、{years} 年经验、地区 {country}，预测区间围绕 ${salary:,} 展开。",
            f"技能数量 {len(skills)} 项会影响岗位稀缺度，但在 demo 数据中权重低于经验和地区。",
        ]
        return {
            "available": True,
            "method": "SHAP feature importance from embedded demo data",
            "top_features": base,
            "narrative": narrative,
        }


salary_explain_service = SalaryExplainService()
