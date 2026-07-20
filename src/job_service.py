"""Shared job list building for reminders and bot commands."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from src.applied_jobs import filter_unapplied
from src.enrich_jobs import enrich_jobs
from src.fetch_jobs import (
    fetch_ctgoodjobs,
    fetch_jobsdb_search,
    fetch_linkedin_search,
    load_seed_jobs,
)
from src.filter_jobs import rank_jobs
from src.telegram_notify import (
    build_applied_message,
    build_message,
    display_limit_from_config,
)


def load_config(root: Path) -> dict:
    with open(root / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect_jobs(config: dict, root: Path) -> list:
    jobs = load_seed_jobs(str(root / "jobs_seed.json"))
    sources = config.get("sources") or {}

    try:
        live = fetch_ctgoodjobs(sources.get("ctgoodjobs_url", ""))
        jobs.extend(live)
    except Exception:
        pass

    keywords = sources.get("jobsdb_keywords") or ["hr officer", "human resources officer"]
    for keyword in keywords:
        try:
            jobs.extend(fetch_jobsdb_search(keyword))
        except Exception:
            pass

    if sources.get("linkedin_enabled", False):
        try:
            jobs.extend(
                fetch_linkedin_search(
                    keywords=sources.get(
                        "linkedin_keywords",
                        '"HR Officer" OR "Human Resources Officer" OR "Senior HR Officer"',
                    )
                )
            )
        except Exception:
            pass

    return enrich_jobs(jobs, root)


def build_ranked_jobs(root: Path, limit: int | None = None) -> list:
    config = load_config(root)
    jobs = collect_jobs(config, root)
    jobs = filter_unapplied(jobs, root)
    return rank_jobs(jobs, config, limit=limit)


def save_cache(root: Path, ranked, slot: str = "manual") -> None:
    cache_dir = root / "data"
    cache_dir.mkdir(exist_ok=True)
    payload = {
        "updated_at": datetime.now().isoformat(),
        "slot": slot,
        "jobs": [
            {
                "rank": i,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "url": job.url,
                "posted_date": job.posted_date,
                "score": score,
                "reasons": reasons,
            }
            for i, (job, score, reasons) in enumerate(ranked, start=1)
        ],
    }
    with open(cache_dir / "cache.json", "w", encoding="utf-8") as f:
        import json

        json.dump(payload, f, ensure_ascii=False, indent=2)


def build_job_list_message(root: Path, slot_label: str = "即時") -> str:
    config = load_config(root)
    ranked = build_ranked_jobs(root)
    limit = display_limit_from_config(config)
    save_cache(root, ranked[:limit], slot="manual")
    return build_message(ranked, slot_label, display_limit=limit)


def build_applied_list_message(root: Path) -> str:
    from src.applied_jobs import list_applied_entries

    return build_applied_message(list_applied_entries(root))
