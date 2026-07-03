"""Fetch and cache job metadata (date, company, location, title) from detail pages."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

from src.date_utils import parse_posted_date
from src.fetch_jobs import Job, TIMEOUT, USER_AGENT

CACHE_TTL = timedelta(hours=12)
JOBPOSTING_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
DATE_RE = re.compile(r'"datePosted"\s*:\s*"([^"]+)"')
TITLE_RE = re.compile(r'"title"\s*:\s*"([^"]+)"')
COMPANY_RE = re.compile(r'"hiringOrganization"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"')


def _cache_path(root: Path) -> Path:
    return root / "data" / "job_detail_cache.json"


def _load_cache(root: Path) -> Dict[str, dict]:
    path = _cache_path(root)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_cache(root: Path, cache: Dict[str, dict]) -> None:
    path = _cache_path(root)
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _cache_fresh(entry: Optional[dict]) -> bool:
    if not entry:
        return False
    fetched_at = datetime.fromisoformat(entry["fetched_at"])
    return datetime.now() - fetched_at <= CACHE_TTL


def _extract_location(job_location) -> str:
    if not job_location:
        return ""
    if isinstance(job_location, list):
        job_location = job_location[0] if job_location else {}
    address = job_location.get("address", {}) if isinstance(job_location, dict) else {}
    for key in ("addressLocality", "addressRegion", "streetAddress"):
        value = address.get(key)
        if value and value not in ("Hong Kong", "HK"):
            return str(value)
    return str(address.get("addressLocality") or address.get("streetAddress") or "")


def _parse_jobposting(html: str) -> dict:
    details = {
        "posted_date": None,
        "title": None,
        "company": None,
        "location": None,
    }

    for block in JOBPOSTING_RE.findall(html):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or data.get("@type") != "JobPosting":
            continue

        posted = parse_posted_date(data.get("datePosted"))
        if posted:
            details["posted_date"] = posted.isoformat()

        if data.get("title"):
            details["title"] = str(data["title"]).strip()

        org = data.get("hiringOrganization") or {}
        if isinstance(org, dict) and org.get("name"):
            details["company"] = str(org["name"]).strip()

        location = _extract_location(data.get("jobLocation"))
        if location:
            details["location"] = location
        break

    if not details["posted_date"]:
        match = DATE_RE.search(html)
        if match:
            posted = parse_posted_date(match.group(1))
            if posted:
                details["posted_date"] = posted.isoformat()

    if not details["title"]:
        match = TITLE_RE.search(html)
        if match:
            details["title"] = match.group(1).strip()

    if not details["company"]:
        match = COMPANY_RE.search(html)
        if match:
            details["company"] = match.group(1).strip()

    return details


def fetch_job_details_from_url(url: str) -> dict:
    host = urlparse(url).netloc.lower()
    if "jobsdb.com" in host:
        return {}

    if not any(domain in host for domain in ("ctgoodjobs.hk", "recruit.com.hk")):
        return {}

    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "zh-HK,en;q=0.9"},
        timeout=TIMEOUT,
    )
    if response.status_code >= 400:
        return {}

    return _parse_jobposting(response.text)


def _looks_mojibake(text: str) -> bool:
    return any(fragment in text for fragment in ("Ã", "é«", "å", "äº", "ç´"))


def _needs_detail_fetch(job: Job) -> bool:
    host = urlparse(job.url).netloc.lower()
    if "jobsdb.com" in host:
        return False
    if not any(domain in host for domain in ("ctgoodjobs.hk", "recruit.com.hk")):
        return False
    if job.company in ("", "(see listing)"):
        return True
    if not job.posted_date:
        return True
    if _looks_mojibake(job.title):
        return True
    return False


def enrich_jobs(jobs: List[Job], root: Path, pause_seconds: float = 0.15) -> List[Job]:
    cache = _load_cache(root)
    enriched: List[Job] = []

    for job in jobs:
        title = job.title
        company = job.company
        location = job.location
        posted_date = job.posted_date
        source = normalize_source(job.url, job.source)

        cached = cache.get(job.url)
        details = cached if _cache_fresh(cached) else None

        if details is None and _needs_detail_fetch(job):
            fetched = fetch_job_details_from_url(job.url)
            details = {
                **fetched,
                "fetched_at": datetime.now().isoformat(timespec="seconds"),
            }
            cache[job.url] = details
            time.sleep(pause_seconds)
        elif details is None and cached:
            details = cached

        if details:
            posted_date = posted_date or details.get("posted_date")
            if details.get("title"):
                title = details["title"]
            if company in ("", "(see listing)") and details.get("company"):
                company = details["company"]
            if not location and details.get("location"):
                location = details["location"]

        enriched.append(
            Job(
                title=title,
                company=company,
                location=location,
                url=job.url,
                source=source,
                score_boost=job.score_boost,
                note=job.note,
                posted_date=posted_date,
            )
        )

    _save_cache(root, cache)
    return enriched


def normalize_source(url: str, fallback: str = "") -> str:
    host = urlparse(url).netloc.lower()
    if "jobsdb.com" in host:
        return "JobsDB"
    if "ctgoodjobs.hk" in host:
        return "CTgoodjobs"
    if "recruit.com.hk" in host:
        return "Recruit.com.hk"
    return fallback or "Unknown"
