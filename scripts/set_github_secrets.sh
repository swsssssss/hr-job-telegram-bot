#!/bin/bash
# Run once on your Mac after: brew install gh && gh auth login
set -euo pipefail

REPO="swsssssss/hr-job-telegram-bot"

if ! gh auth status >/dev/null 2>&1; then
  echo "Please run: gh auth login"
  exit 1
fi

read -r -p "Paste TELEGRAM_BOT_TOKEN: " TOKEN
read -r -p "Paste TELEGRAM_CHAT_ID [6340221598]: " CHAT_ID
CHAT_ID="${CHAT_ID:-6340221598}"

gh secret set TELEGRAM_BOT_TOKEN -R "$REPO" -b"$TOKEN"
gh secret set TELEGRAM_CHAT_ID -R "$REPO" -b"$CHAT_ID"

echo ""
echo "Done. Test at:"
echo "https://github.com/swsssssss/hr-job-telegram-bot/actions/workflows/send-reminders.yml"
