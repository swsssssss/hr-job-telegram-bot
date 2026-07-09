"""Filter and rank jobs against user criteria."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from src.date_utils import format_posted_label, is_within_max_age
from src.fetch_jobs import Job


def _contains_any(text: str, keywords: List[str]) -> bool:
    lowered = text.lower()
    return any(k.lower() in lowered for k in keywords)


def _extract_salary(text: str) -> Optional[int]:
    match = re.search(r"\$\s*(\d{1,3})\s*[kK]", text)
    if match:
        return int(match.group(1)) * 1000
    match = re.search(r"(\d{2,3}),?000", text)
    if match:
        value = int(match.group(1))
        return value * 1000 if value < 1000 else value
    return None


def _title_matches(title: str, keywords: List[str]) -> bool:
    lowered = title.lower()
    if _contains_any(lowered, keywords):
        return True
    # Handle titles like "Officer, Human Resources"
    if "human resources" in lowered and "officer" in lowered:
        return True
    if "hr" in lowered and "officer" in lowered:
        return True
    return False


def _is_assistant_hr_role(title: str) -> bool:
    lowered = title.lower()
    if "administrative" in lowered:
        return False
    return bool(re.search(r"\bassistant\b", lowered) and ("hr" in lowered or "human resources" in lowered))


def score_job(job: Job, config: Dict) -> Tuple[int, List[str]]:
    criteria = config["criteria"]
    reasons: List[str] = []
    score = job.score_boost

    title = job.title or ""
    company = job.company or ""
    location = job.location or ""

    if _contains_any(company, criteria.get("exclude_companies", [])):
        return -999, ["excluded company"]

    blob = f"{title} {company} {location} {job.note}"
    if _contains_any(blob, criteria.get("exclude_company_keywords", [])):
        return -999, ["excluded agency/recruiter"]

    if _contains_any(blob, criteria.get("exclude_institution_keywords", [])):
        return -999, ["excluded institution"]

    if not _title_matches(title, criteria.get("title_keywords", [])):
        return -999, ["title mismatch"]

    if _contains_any(title, criteria.get("exclude_title_keywords", [])):
        return -999, ["excluded title keyword"]

    salary = _extract_salary(blob)
    if _is_assistant_hr_role(title):
        assistant_min = criteria.get("assistant_min_salary", 30000)
        if salary is None or salary <= assistant_min:
            return -999, [f"assistant role needs >${assistant_min:,} salary"]

    max_post_age_days = criteria.get("max_post_age_days", 9)
    if not is_within_max_age(job.posted_date, max_post_age_days):
        if job.posted_date:
            return -999, [f"posted over {max_post_age_days} days ago"]
        return -999, ["post date unknown"]

    if salary is not None:
        if salary >= criteria.get("min_salary", 28000):
            score += 8
            reasons.append(f"salary ~${salary:,}")
        else:
            score -= 5
            reasons.append(f"salary below target (${salary:,})")

    if location and _contains_any(location, criteria.get("preferred_locations", [])):
        score += 10
        reasons.append("preferred location")

    if _contains_any(company, criteria.get("boost_companies", [])):
        score += 6
        reasons.append("preferred company")

    if _contains_any(title, ["senior hr", "sr hr"]):
        score += 3

    if job.note:
        score += 2

    if job.posted_date:
        reasons.append(format_posted_label(job.posted_date))

    return score, reasons


def rank_jobs(
    jobs: List[Job],
    config: Dict,
    limit: int | None = None,
) -> List[Tuple[Job, int, List[str]]]:
    if limit is None:
        limit = int(config.get("criteria", {}).get("list_limit", 0))
    ranked: List[Tuple[Job, int, List[str]]] = []
    seen = set()
    for job in jobs:
        key = job.key()
        if key in seen:
            continue
        seen.add(key)
        score, reasons = score_job(job, config)
        if score >= 0:
            ranked.append((job, score, reasons))

    ranked.sort(key=lambda row: row[1], reverse=True)
    if limit > 0:
        return ranked[:limit]
    return ranked
