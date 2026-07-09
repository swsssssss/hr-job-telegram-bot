#!/usr/bin/env python3
"""Map GitHub Actions cron (UTC) to reminder slot for Hong Kong time."""

from __future__ import annotations

import sys

# 08:00 HKT = 00:xx UTC — backup every 5 min (schedule_guard keeps 07:55–08:30)
MORNING_CRONS = {f"{minute} 0 * * *" for minute in range(0, 60, 5)}

# 20:00 HKT = 12:xx UTC — backup every 5 min (schedule_guard keeps 19:55–20:30)
EVENING_CRONS = {f"{minute} 12 * * *" for minute in range(0, 60, 5)}


def resolve(cron: str, manual_slot: str = "morning") -> str:
    if cron in MORNING_CRONS:
        return "morning"
    if cron in EVENING_CRONS:
        return "evening"
    return manual_slot


def main() -> int:
    cron = sys.argv[1] if len(sys.argv) > 1 else ""
    manual = sys.argv[2] if len(sys.argv) > 2 else "morning"
    print(resolve(cron, manual))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
