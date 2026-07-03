#!/usr/bin/env python3
"""Always-on Telegram listener for instant bot replies."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.telegram_commands import process_telegram_commands  # noqa: E402

POLL_SECONDS = 30


def main() -> int:
    load_dotenv(ROOT / ".env")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env", file=sys.stderr)
        return 1

    print("HR job bot listener started.", flush=True)
    while True:
        try:
            replies = process_telegram_commands(
                token,
                chat_id,
                ROOT,
                long_poll_seconds=POLL_SECONDS,
            )
            if replies:
                print(f"Handled {len(replies)} message(s).", flush=True)
        except Exception as exc:
            print(f"[warn] listener error: {exc}", file=sys.stderr, flush=True)
            time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
