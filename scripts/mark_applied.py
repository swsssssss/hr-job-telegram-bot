#!/usr/bin/env python3
"""CLI helper to mark jobs as applied."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.applied_jobs import (  # noqa: E402
    load_applied,
    mark_applied,
    mark_applied_by_rank,
    unmark_applied,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Mark HR jobs as applied")
    parser.add_argument("ranks", nargs="*", type=int, help="Rank numbers from last Telegram list")
    parser.add_argument("--url", help="Job URL to mark as applied")
    parser.add_argument("--undo-url", help="Remove applied record for URL")
    parser.add_argument("--list", action="store_true", help="List applied jobs")
    args = parser.parse_args()

    if args.list:
        applied = load_applied(ROOT)
        if not applied:
            print("No applied jobs yet.")
            return 0
        for idx, entry in enumerate(applied.values(), start=1):
            print(f"{idx}. {entry.get('title')} | {entry.get('company')} | {entry.get('url')}")
        return 0

    if args.undo_url:
        removed = unmark_applied(ROOT, args.undo_url)
        print("Removed." if removed else "Not found.")
        return 0

    if args.url:
        mark_applied(ROOT, args.url)
        print(f"Marked applied: {args.url}")
        return 0

    if args.ranks:
        marked = mark_applied_by_rank(ROOT, args.ranks)
        if not marked:
            print("No matching ranks in last cache.json")
            return 1
        for entry in marked:
            print(f"Marked applied: {entry.get('title')} | {entry.get('url')}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
