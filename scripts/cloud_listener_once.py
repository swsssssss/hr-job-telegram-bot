#!/usr/bin/env python3
"""Single-shot Telegram poll for GitHub Actions (no long-running listener)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.telegram_commands import process_telegram_commands  # noqa: E402


def main() -> int:
    load_dotenv(ROOT / ".env")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID", file=sys.stderr)
        return 1

    replies = process_telegram_commands(token, chat_id, ROOT, long_poll_seconds=0)
    print(f"Handled {len(replies)} message(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
