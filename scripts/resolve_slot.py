#!/usr/bin/env python3
"""Map GitHub Actions cron (UTC) to reminder slot for Hong Kong time."""

from __future__ import annotations

import sys

# GitHub passes comma-separated crons as one string, e.g.
# "0,5,10,15,20,25,30,35,40,45,50,55 0 * * *"


def resolve(cron: str, manual_slot: str = "morning") -> str:
    cron = cron.strip()
    if not cron:
        return manual_slot

    parts = cron.split()
    if len(parts) >= 2:
        hour = parts[1]
        if hour == "0":
            return "morning"
        if hour == "12":
            return "evening"

    return manual_slot


def main() -> int:
    cron = sys.argv[1] if len(sys.argv) > 1 else ""
    manual = sys.argv[2] if len(sys.argv) > 2 else "morning"
    print(resolve(cron, manual))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
