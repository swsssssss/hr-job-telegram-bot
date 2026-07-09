"""Hong Kong time windows for scheduled reminder slots."""

from __future__ import annotations

from src.date_utils import now_hkt

# Minutes from midnight HKT
MORNING_TARGET = 8 * 60  # 08:00
EVENING_TARGET = 20 * 60  # 20:00
WINDOW_BEFORE_MIN = 5
WINDOW_AFTER_MIN = 30


def _minutes_now() -> int:
    now = now_hkt()
    return now.hour * 60 + now.minute


def should_send_slot(slot: str, *, force: bool = False) -> bool:
    if force:
        return True
    if slot == "applied_summary":
        return False

    minutes = _minutes_now()
    if slot == "morning":
        start = MORNING_TARGET - WINDOW_BEFORE_MIN
        end = MORNING_TARGET + WINDOW_AFTER_MIN
        return start <= minutes <= end

    if slot == "evening":
        start = EVENING_TARGET - WINDOW_BEFORE_MIN
        end = EVENING_TARGET + WINDOW_AFTER_MIN
        return start <= minutes <= end

    return True
