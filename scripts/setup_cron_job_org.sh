#!/bin/bash
# Optional: use cron-job.org for exact 08:00 / 20:00 HKT delivery.
set -euo pipefail

REPO="swsssssss/hr-job-telegram-bot"

echo "=== 準時 08:00 / 20:00 HKT（cron-job.org）==="
echo ""
echo "GitHub Actions 免費 cron 可能遲到。想準時 send，用 cron-job.org："
echo ""
echo "1. 註冊 https://cron-job.org （免費）"
echo "2. Create cronjob × 2："
echo ""
echo "   Job A — 朝早 08:00 HKT"
echo "   URL: POST https://api.github.com/repos/${REPO}/dispatches"
echo "   Headers:"
echo "     Accept: application/vnd.github+json"
echo "     Authorization: Bearer <你的 GitHub PAT>"
echo "   Body (JSON):"
echo '     {"event_type":"morning_reminder"}'
echo "   Schedule: 08:00, Timezone: Asia/Hong_Kong"
echo ""
echo "   Job B — 晚間 20:00 HKT"
echo "   Body: {\"event_type\":\"evening_reminder\"}"
echo "   Schedule: 20:00, Timezone: Asia/Hong_Kong"
echo ""
echo "3. GitHub PAT 需要 repo scope"
echo ""
echo "GitHub Actions schedule 仍會做 backup（07:55–08:30 / 19:55–20:30 HKT）"
echo ""
