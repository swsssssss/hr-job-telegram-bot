"""Parse and validate job posting dates."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional, Union


def parse_posted_date(value: Union[str, date, datetime, None]) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def days_since_posted(value: Union[str, date, datetime, None], today: Optional[date] = None) -> Optional[int]:
    posted = parse_posted_date(value)
    if posted is None:
        return None
    ref = today or date.today()
    return (ref - posted).days


def is_within_max_age(
    value: Union[str, date, datetime, None],
    max_days: int,
    today: Optional[date] = None,
) -> bool:
    age = days_since_posted(value, today=today)
    if age is None:
        return False
    return 0 <= age <= max_days


def format_posted_label(value: Union[str, date, datetime, None]) -> str:
    age = days_since_posted(value)
    posted = parse_posted_date(value)
    if age is None or posted is None:
        return "Post date unknown"
    if age == 0:
        return f"Posted today ({posted.isoformat()})"
    if age == 1:
        return f"Posted 1 day ago ({posted.isoformat()})"
    return f"Posted {age} days ago ({posted.isoformat()})"
