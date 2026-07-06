"""Prevent duplicate reminder sends when backup cron jobs run."""

from __future__ import annotations

import json
from pathlib import Path

from src.date_utils import today_hkt

STATE_FILE = "last_sent_slots.json"


def _state_path(root: Path) -> Path:
    return root / "data" / STATE_FILE


def _today_hkt() -> str:
    return today_hkt().isoformat()


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
