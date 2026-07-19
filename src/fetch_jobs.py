"""Fetch HR job listings from supported sources."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.parse import unquote

import requests

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
TIMEOUT = 25

JOBSDB_SEARCH_URL = "https://hk.jobsdb.com/api/jobsearch/v5/search"
LINKEDIN_GUEST_SEARCH_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
)

WHITESPACE_RE = re.compile(r"\s+")
CT_LISTITEM_RE = re.compile(
    r'\{"@type":"ListItem","position":(\d+),"url":"([^"]+)","name":"([^"]+)"\}'
)
LINKEDIN_CARD_RE = re.compile(
    r'data-entity-urn="urn:li:jobPosting:(\d+)".*?'
    r'href="(https://[^"]+/jobs/view/[^"]+)"'
    r'.*?<h3[^>]*class="base-search-card__title"[^>]*>\s*(.*?)\s*</h3>'
    r'.*?<h4[^>]*class="base-search-card__subtitle"[^>]*>\s*<a[^>]*>\s*(.*?)\s*</a>'
    r'(?:.*?<span class="job-search-card__location">\s*(.*?)\s*</span>)?'
    r'(?:.*?<time[^>]*datetime="([^"]+)")?',
    re.S,
)


@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    source: str
    score_boost: int = 0
    note: str = ""
    posted_date: Optional[str] = None

    def key(self) -> str:
        return self.url.rstrip("/").lower()


def _session_headers(*, accept: str = "text/html,application/xhtml+xml", referer: str = "") -> dict:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": accept,
        "Accept-Language": "zh-HK,en-HK;q=0.9,en;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def _clean_text(value: str) -> str:
    text = html.unescape(value or "")
    return WHITESPACE_RE.sub(" ", text).strip()


def _jobsdb_location(row: dict) -> str:
    locations = row.get("locations") or []
    if not locations:
        return ""
    first = locations[0] if isinstance(locations, list) else locations
    if isinstance(first, dict):
        return str(first.get("label") or "").strip()
    return str(first).strip()


def _jobsdb_company(row: dict) -> str:
    advertiser = row.get("advertiser") or {}
    if isinstance(advertiser, dict) and advertiser.get("description"):
        return str(advertiser["description"]).strip()
    employer = row.get("employer") or {}
    if isinstance(employer, dict) and employer.get("name"):
        return str(employer["name"]).strip()
    return str(row.get("companyName") or "").strip()


def _jobsdb_posted_date(row: dict) -> Optional[str]:
    listing_date = row.get("listingDate") or ""
    if not listing_date:
        return None
    # API returns ISO timestamps like 2026-07-18T12:36:05Z
    return str(listing_date)[:10]


def _jobsdb_note(row: dict) -> str:
    parts: List[str] = []
    salary = str(row.get("salaryLabel") or "").strip()
    if salary:
        parts.append(salary)
    teaser = str(row.get("teaser") or "").strip()
    if teaser:
        parts.append(teaser[:160])
    return " | ".join(parts)


def fetch_jobsdb_search(
    keyword: str = "hr officer",
    page_size: int = 50,
    max_pages: int = 2,
) -> List[Job]:
    """Fetch JobsDB listings via the public JSON search API.

    HTML search pages are Cloudflare-protected; the /api/jobsearch/v5/search
    endpoint still returns structured results with title/company/location/date.
    """
    jobs: List[Job] = []
    seen = set()
    headers = _session_headers(
        accept="application/json, text/plain, */*",
        referer=f"https://hk.jobsdb.com/{keyword.strip().lower().replace(' ', '-')}-jobs",
    )

    for page in range(1, max_pages + 1):
        params = {
            "siteKey": "HK-Main",
            "sourcesystem": "houston",
            "keywords": keyword,
            "page": str(page),
            "pageSize": str(page_size),
            "locale": "en-HK",
        }
        response = requests.get(
            JOBSDB_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=TIMEOUT,
        )
        if response.status_code >= 400:
            break

        payload = response.json()
        rows = payload.get("data") or []
        if not rows:
            break

        for row in rows:
            job_id = str(row.get("id") or "").strip()
            title = str(row.get("title") or "").strip()
            if not job_id or not title or job_id in seen:
                continue
            seen.add(job_id)
            jobs.append(
                Job(
                    title=title,
                    company=_jobsdb_company(row),
                    location=_jobsdb_location(row),
                    url=f"https://hk.jobsdb.com/job/{job_id}",
                    source="JobsDB",
                    note=_jobsdb_note(row),
                    posted_date=_jobsdb_posted_date(row),
                )
            )

    return jobs


def fetch_ctgoodjobs(url: str) -> List[Job]:
    """Parse CTgoodjobs search page JSON embedded in HTML.

    CTgoodjobs often serves a human-verification wall to datacenter IPs.
    Callers should treat failures as non-fatal.
    """
    response = requests.get(
        url,
        headers=_session_headers(referer="https://jobs.ctgoodjobs.hk/"),
        timeout=TIMEOUT,
    )
    html_text = response.text
    if response.status_code >= 400 or (
        "Human Verification" in html_text and "ListItem" not in html_text
    ):
        raise RuntimeError(
            f"CTgoodjobs blocked or unavailable (HTTP {response.status_code})"
        )

    jobs: List[Job] = []
    seen = set()
    for _pos, job_url, name in CT_LISTITEM_RE.findall(html_text):
        if job_url in seen:
            continue
        seen.add(job_url)
        jobs.append(
            Job(
                title=name.strip(),
                company="",
                location="",
                url=job_url,
                source="CTgoodjobs",
            )
        )
    return jobs


def fetch_linkedin_search(
    keywords: str = '"HR Officer" OR "Human Resources Officer" OR "Senior HR Officer"',
    location: str = "Hong Kong",
    pages: int = 3,
    page_size: int = 25,
    posted_within_seconds: int = 60 * 60 * 24 * 14,
) -> List[Job]:
    """Fetch LinkedIn guest job cards (works without login)."""
    jobs: List[Job] = []
    seen = set()
    headers = _session_headers(referer="https://www.linkedin.com/jobs/search/")

    for page_index in range(pages):
        params = {
            "keywords": keywords,
            "location": location,
            "start": page_index * page_size,
            "f_TPR": f"r{posted_within_seconds}",
        }
        response = requests.get(
            LINKEDIN_GUEST_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=TIMEOUT,
        )
        if response.status_code >= 400:
            break

        html_text = response.text
        matches = LINKEDIN_CARD_RE.findall(html_text)
        if not matches:
            break

        for job_id, raw_url, title, company, loc, posted in matches:
            if job_id in seen:
                continue
            seen.add(job_id)
            clean_url = unquote(html.unescape(raw_url)).split("?")[0]
            jobs.append(
                Job(
                    title=_clean_text(title),
                    company=_clean_text(company),
                    location=_clean_text(loc),
                    url=clean_url,
                    source="LinkedIn",
                    posted_date=(posted[:10] if posted else None),
                )
            )

    return jobs


def load_seed_jobs(path: str) -> List[Job]:
    import json

    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    return [Job(**row) for row in rows]


def job_to_dict(job: Job) -> dict:
    return asdict(job)
