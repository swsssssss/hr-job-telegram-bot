#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Creating virtual environment"
python3 -m venv venv
source venv/bin/activate

echo "==> Installing dependencies"
pip install -q --upgrade pip
pip install -q -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

mkdir -p data logs

echo ""
echo "=== 下一步（Telegram setup）==="
echo "1. Telegram 搵 @BotFather → /newbot → 拎 Bot Token"
echo "2. 將 Token 填入 $ROOT/.env 嘅 TELEGRAM_BOT_TOKEN"
echo "3. 喺 Telegram 同你個 bot 講 /start"
echo "4. 跑: source venv/bin/activate && python scripts/get_chat_id.py"
echo "5. 將 chat id 填入 .env 嘅 TELEGRAM_CHAT_ID"
echo "6. 測試: python src/main.py --dry-run"
echo "7. 真 send: python src/main.py --slot morning"
echo "8. 裝定時: bash scripts/install_launchd.sh"
echo ""
