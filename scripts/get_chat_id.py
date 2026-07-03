#!/usr/bin/env python3
"""Helper: fetch Telegram chat_id after you message your bot."""

import os
import sys

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))

token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not token:
    print("Set TELEGRAM_BOT_TOKEN in .env first.")
    sys.exit(1)

print("1) Open Telegram and send /start to your bot")
print("2) Press Enter here after sending...")
input()

resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=30)
resp.raise_for_status()
data = resp.json()
if not data.get("ok"):
    print("API error:", data)
    sys.exit(1)

updates = data.get("result", [])
if not updates:
    print("No messages found. Send /start to your bot and run again.")
    sys.exit(1)

chat = updates[-1]["message"]["chat"]
chat_id = chat["id"]
name = chat.get("first_name") or chat.get("username") or "user"
print(f"\nYour TELEGRAM_CHAT_ID = {chat_id}  ({name})")
print("Add this line to your .env file.")
