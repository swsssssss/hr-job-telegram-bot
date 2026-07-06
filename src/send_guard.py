"""Prevent duplicate reminder sends when backup cron jobs run."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HKT = timezone(timedelta(hours=8))
STATE_FILE = "last_sent_slots.json"


def _state_path(root: Path) -> Path:
    return root / "data" / STATE_FILE


def _today_hkt() -> str:
    return datetime.now(HKT).strftime("%Y-%m-%d")


def already_sent_today(root: Path, slot: str) -> bool:
    path = _state_path(root)
    if not path.exists():
        return False
    with open(path, encoding="utf-8") as f:
        state = json.load(f)
    return state.get(slot) == _today_hkt()


def mark_sent_today(root: Path, slot: str) -> None:
    path = _state_path(root)
    path.parent.mkdir(exist_ok=True)
    state = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    state[slot] = _today_hkt()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
