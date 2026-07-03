"""Fetch HR job listings from supported sources."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import List, Optional

import requests

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
TIMEOUT = 25


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


def fetch_ctgoodjobs(url: str) -> List[Job]:
    """Parse CTgoodjobs search page JSON embedded in HTML."""
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "zh-HK,en;q=0.9"},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    html = response.text
    pattern = re.compile(
        r'\{"@type":"ListItem","position":(\d+),"url":"([^"]+)","name":"([^"]+)"\}'
    )
    jobs: List[Job] = []
    seen = set()
    for _pos, job_url, name in pattern.findall(html):
        if job_url in seen:
            continue
        seen.add(job_url)
        title = name.strip()
        jobs.append(
            Job(
                title=title,
                company="",
                location="",
                url=job_url,
                source="CTgoodjobs",
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
