#!/usr/bin/env python3
"""Daily HR job hunt reminder – fetch, rank, send to Telegram."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.applied_jobs import filter_unapplied, list_applied_entries  # noqa: E402
from src.enrich_jobs import enrich_jobs  # noqa: E402
from src.fetch_jobs import fetch_ctgoodjobs, fetch_jobsdb_search, load_seed_jobs  # noqa: E402
from src.filter_jobs import rank_jobs  # noqa: E402
from src.telegram_commands import process_telegram_commands  # noqa: E402
from src.send_guard import already_sent_today, mark_sent_today  # noqa: E402
from src.telegram_notify import (  # noqa: E402
    build_applied_message,
    build_message,
    send_telegram_message,
)

SLOT_LABELS = {
    "morning": "朝早",
    "evening": "晚間",
    "applied_summary": "晚間已 Apply",
}


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect_jobs(config: dict) -> list:
    jobs = load_seed_jobs(str(ROOT / "jobs_seed.json"))
    try:
        live = fetch_ctgoodjobs(config["sources"]["ctgoodjobs_url"])
        jobs.extend(live)
    except Exception as exc:
        print(f"[warn] CTgoodjobs fetch failed: {exc}", file=sys.stderr)
    try:
        jobsdb = fetch_jobsdb_search("hr officer")
        jobs.extend(jobsdb)
        print(f"[info] JobsDB search returned {len(jobsdb)} jobs.", file=sys.stderr)
    except Exception as exc:
        print(f"[warn] JobsDB fetch failed: {exc}", file=sys.stderr)
    return enrich_jobs(jobs, ROOT)


def save_cache(ranked, slot: str) -> None:
    cache_dir = ROOT / "data"
    cache_dir.mkdir(exist_ok=True)
    payload = {
        "updated_at": datetime.now().isoformat(),
        "slot": slot,
        "jobs": [
            {
                "rank": i,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "url": job.url,
                "posted_date": job.posted_date,
                "score": score,
                "reasons": reasons,
            }
            for i, (job, score, reasons) in enumerate(ranked, start=1)
        ],
    }
    with open(cache_dir / "cache.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def send_job_reminder(slot: str, config: dict, dry_run: bool) -> tuple[str, int]:
    slot_label = SLOT_LABELS[slot]
    jobs = collect_jobs(config)
    jobs = filter_unapplied(jobs, ROOT)
    ranked = rank_jobs(jobs, config, limit=10)
    message = build_message(ranked, slot_label)
    save_cache(ranked, slot)
    return message, len(ranked)


def send_applied_summary(dry_run: bool) -> tuple[str, int]:
    entries = list_applied_entries(ROOT)
    message = build_applied_message(entries)
    return message, len(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send HR job hunt reminder to Telegram")
    parser.add_argument(
        "--slot",
        choices=["morning", "evening", "applied_summary"],
        default="morning",
        help="Reminder slot label",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print message without sending to Telegram",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Send even if this slot was already sent today",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.force and already_sent_today(ROOT, args.slot):
        print(f"Already sent {args.slot} today ({SLOT_LABELS[args.slot]}), skipping.")
        return 0

    load_dotenv(ROOT / ".env")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if token and chat_id and not args.dry_run:
        try:
            process_telegram_commands(token, chat_id, ROOT)
        except Exception as exc:
            print(f"[warn] Telegram command processing failed: {exc}", file=sys.stderr)

    if args.slot == "applied_summary":
        message, count = send_applied_summary(args.dry_run)
        slot_label = SLOT_LABELS[args.slot]
    else:
        config = load_config()
        message, count = send_job_reminder(args.slot, config, args.dry_run)
        slot_label = SLOT_LABELS[args.slot]

    if args.dry_run:
        print(message.replace("<b>", "**").replace("</b>", "**"))
        return 0

    if not token or not chat_id:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env", file=sys.stderr)
        return 1

    send_telegram_message(token, chat_id, message)
    mark_sent_today(ROOT, args.slot)
    if args.slot == "applied_summary":
        print(f"Sent {slot_label} applied summary with {count} jobs.")
    else:
        print(f"Sent {slot_label} reminder with {count} jobs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
