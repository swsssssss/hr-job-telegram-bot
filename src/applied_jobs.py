"""Track jobs the user has already applied for."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from src.fetch_jobs import Job


def _applied_path(root: Path) -> Path:
    return root / "data" / "applied_jobs.json"


def job_key(url: str) -> str:
    normalized = url.rstrip("/").lower()
    match = re.search(r"/job/(\d+)", normalized)
    if match:
        return f"jobsdb:{match.group(1)}"
    match = re.search(r"ctgoodjobs\.hk/job/(\d+)", normalized)
    if match:
        return f"ctgoodjobs:{match.group(1)}"
    match = re.search(r"recruit\.com\.hk/job-detail/[^/]+/([^/?#]+)", normalized)
    if match:
        return f"recruit:{match.group(1).lower()}"
    return normalized


def load_applied(root: Path) -> Dict[str, dict]:
    path = _applied_path(root)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_applied(root: Path, applied: Dict[str, dict]) -> None:
    path = _applied_path(root)
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(applied, f, ensure_ascii=False, indent=2)


def is_applied(url: str, root: Path) -> bool:
    return job_key(url) in load_applied(root)


def mark_applied(
    root: Path,
    url: str,
    title: str = "",
    company: str = "",
) -> dict:
    applied = load_applied(root)
    key = job_key(url)
    entry = {
        "url": url,
        "title": title,
        "company": company,
        "applied_at": datetime.now().isoformat(timespec="seconds"),
    }
    applied[key] = entry
    save_applied(root, applied)
    return entry


def unmark_applied(root: Path, url: str) -> bool:
    applied = load_applied(root)
    key = job_key(url)
    if key not in applied:
        return False
    del applied[key]
    save_applied(root, applied)
    return True


def _normalize_company(name: str) -> str:
    lowered = name.lower().strip()
    for token in (
        "limited",
        "ltd",
        "company",
        "co.",
        "group",
        "international",
        "hong kong",
        "（",
        "(",
        "|",
        "  ",
    ):
        lowered = lowered.replace(token, " ")
    return " ".join(lowered.split())


def _company_matches(applied_name: str, job_company: str) -> bool:
    applied = _normalize_company(applied_name)
    company = _normalize_company(job_company)
    if not applied or not company:
        return False
    return applied in company or company in applied


def _load_applied_companies(root: Path) -> List[str]:
    config_path = root / "config.yaml"
    if not config_path.exists():
        return []
    import yaml

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    return list(config.get("criteria", {}).get("applied_companies", []))


def filter_unapplied(jobs: List[Job], root: Path) -> List[Job]:
    applied = load_applied(root)
    applied_keys = set(applied.keys())
    applied_names = [
        entry.get("company", "")
        for entry in applied.values()
        if entry.get("company")
    ]
    applied_names.extend(_load_applied_companies(root))

    filtered: List[Job] = []
    for job in jobs:
        if job_key(job.url) in applied_keys:
            continue
        if any(_company_matches(name, job.company) for name in applied_names):
            continue
        filtered.append(job)
    return filtered


def load_last_sent_jobs(root: Path) -> List[dict]:
    cache_path = root / "data" / "cache.json"
    if not cache_path.exists():
        return []
    with open(cache_path, encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("jobs", [])


def mark_applied_by_rank(root: Path, ranks: List[int]) -> List[dict]:
    last_jobs = load_last_sent_jobs(root)
    if not last_jobs:
        return []

    rank_map = {item["rank"]: item for item in last_jobs}
    marked = []
    for rank in ranks:
        item = rank_map.get(rank)
        if not item:
            continue
        marked.append(
            mark_applied(
                root,
                url=item["url"],
                title=item.get("title", ""),
                company=item.get("company", ""),
            )
        )
    return marked


def _find_job_by_keyword(root: Path, keyword: str) -> Optional[dict]:
    needle = keyword.lower().strip()
    if not needle:
        return None

    for item in load_last_sent_jobs(root):
        company = (item.get("company") or "").lower()
        title = (item.get("title") or "").lower()
        if needle in company or needle in title:
            return item

    seed_path = root / "jobs_seed.json"
    if seed_path.exists():
        with open(seed_path, encoding="utf-8") as f:
            seed_rows = json.load(f)
        for row in seed_rows:
            company = (row.get("company") or "").lower()
            title = (row.get("title") or "").lower()
            if needle in company or needle in title:
                return row
    return None


def mark_applied_by_company(root: Path, keyword: str) -> Optional[dict]:
    item = _find_job_by_keyword(root, keyword)
    if not item:
        return None
    return mark_applied(
        root,
        url=item["url"],
        title=item.get("title", ""),
        company=item.get("company", ""),
    )


def list_applied_entries(root: Path) -> List[dict]:
    applied = load_applied(root)
    entries = list(applied.values())
    entries.sort(key=lambda item: item.get("applied_at", ""), reverse=True)
    return entries
