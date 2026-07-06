#!/usr/bin/env python3
"""Map GitHub Actions cron (UTC) to reminder slot for Hong Kong time."""

from __future__ import annotations

import sys

# GitHub cron uses UTC. Hong Kong = UTC+8.
# Morning 08:00 HKT → 00:00 UTC (+ backups every 30 min until 11:30 HKT)
MORNING_CRONS = {
    "0 0 * * *",
    "30 0 * * *",
    "0 1 * * *",
    "30 1 * * *",
    "0 2 * * *",
    "30 2 * * *",
    "0 3 * * *",
    "30 3 * * *",
}

# Evening 20:00 HKT → 12:00 UTC (+ backups every 30 min until 23:30 HKT)
EVENING_CRONS = {
    "0 12 * * *",
    "30 12 * * *",
    "0 13 * * *",
    "30 13 * * *",
    "0 14 * * *",
    "30 14 * * *",
    "0 15 * * *",
    "30 15 * * *",
}

# Applied summary 20:05 HKT → 12:05 UTC (+ backups)
APPLIED_CRONS = {
    "5 12 * * *",
    "35 12 * * *",
    "5 13 * * *",
    "35 13 * * *",
    "5 14 * * *",
    "35 14 * * *",
    "5 15 * * *",
    "35 15 * * *",
}


def resolve(cron: str, manual_slot: str = "morning") -> str:
    if cron in MORNING_CRONS:
        return "morning"
    if cron in EVENING_CRONS:
        return "evening"
    if cron in APPLIED_CRONS:
        return "applied_summary"
    return manual_slot


def main() -> int:
    cron = sys.argv[1] if len(sys.argv) > 1 else ""
    manual = sys.argv[2] if len(sys.argv) > 2 else "morning"
    print(resolve(cron, manual))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
