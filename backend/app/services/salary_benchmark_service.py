from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.services.salary_paths import salary_processed_dir


COUNTRY_BENCHMARKS = {
    "UNITED STATES": 135000,
    "SWITZERLAND": 148000,
    "NORWAY": 132000,
    "DENMARK": 128000,
    "SINGAPORE": 128000,
    "CANADA": 110000,
    "FINLAND": 112000,
    "SWEDEN": 118000,
    "ISRAEL": 118000,
    "GERMANY": 105000,
    "NETHERLANDS": 103000,
    "IRELAND": 101000,
    "AUSTRALIA": 108000,
    "UNITED KINGDOM": 98000,
    "AUSTRIA": 96000,
    "FRANCE": 92000,
    "JAPAN": 82000,
    "SOUTH KOREA": 75000,
    "CHINA": 72000,
    "INDIA": 58000,
}


EXP_MULTIPLIER = {"EN": 0.72, "MI": 1.0, "SE": 1.28, "EX": 1.55}
SIZE_MULTIPLIER = {"S": 0.92, "M": 1.0, "L": 1.12, "unknown": 1.0}
INDUSTRY_MULTIPLIER = {
    "Technology": 1.0,
    "Finance": 1.1,
    "Healthcare": 0.96,
    "Consulting": 1.02,
    "Education": 0.86,
    "Media": 0.9,
    "Retail": 0.88,
    "Transportation": 0.94,
}


def _float(value: Any, fallback: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


class SalaryBenchmarkService:
    @lru_cache(maxsize=1)
    def job_category_salary(self) -> list[dict[str, Any]]:
        path = salary_processed_dir() / "job_category_salary.csv"
        if not path.exists():
            return []
        return self._read_job_category_csv(path)

    def _read_job_category_csv(self, path: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                rows.append(
                    {
                        "category": row.get("job_category") or row.get("category") or "Other AI Roles",
                        "count": int(_float(row.get("count"))),
                        "mean": round(_float(row.get("mean")), 0),
                        "median": round(_float(row.get("median")), 0),
                        "q25": round(_float(row.get("q25")), 0),
                        "q75": round(_float(row.get("q75")), 0),
                    }
                )
        return rows

    def country_benchmark(self, country: str) -> int:
        return int(COUNTRY_BENCHMARKS.get(country.upper().strip(), 100000))

    def heuristic_salary(self, profile: dict[str, Any]) -> int:
        country = str(profile.get("country") or "UNITED STATES").upper().strip()
        exp = str(profile.get("experience_level") or "MI").upper().strip()
        size = str(profile.get("company_size") or "M").upper().strip()
        industry = str(profile.get("industry") or "Technology").strip()
        years = max(0, int(_float(profile.get("years_experience"), 3)))
        remote_ratio = max(0, min(100, int(_float(profile.get("remote_ratio"), 50))))
        skills = profile.get("skills") or []
        skill_count = len(skills) if isinstance(skills, list) else len([s for s in str(skills).split(",") if s.strip()])

        base = self.country_benchmark(country)
        salary = base * EXP_MULTIPLIER.get(exp, 1.0) * SIZE_MULTIPLIER.get(size, 1.0)
        salary *= INDUSTRY_MULTIPLIER.get(industry, 1.0)
        salary *= 1 + min(years, 12) * 0.018
        salary *= 1 + min(skill_count, 12) * 0.012
        salary *= 1 + (remote_ratio - 50) * 0.0008
        return int(round(salary / 1000) * 1000)

    def market_overview(self) -> dict[str, Any]:
        return {
            "country_benchmarks": COUNTRY_BENCHMARKS,
            "job_categories": self.job_category_salary(),
            "top_countries": [
                {"country": country, "salary": salary}
                for country, salary in sorted(COUNTRY_BENCHMARKS.items(), key=lambda item: item[1], reverse=True)[:10]
            ],
        }


salary_benchmark_service = SalaryBenchmarkService()
