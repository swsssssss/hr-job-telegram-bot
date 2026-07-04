#!/bin/bash
set -euo pipefail

# Local Mac scheduler. Prefer cloud instead: bash scripts/setup_cloud.sh

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/venv/bin/python"
MAIN="$ROOT/src/main.py"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$ROOT/logs"

mkdir -p "$LAUNCH_DIR" "$LOG_DIR"

install_plist() {
  local label="$1"
  local slot="$2"
  local hour="$3"
  local minute="$4"
  local plist="$LAUNCH_DIR/${label}.plist"

  cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PY}</string>
    <string>${MAIN}</string>
    <string>--slot</string>
    <string>${slot}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>${hour}</integer>
    <key>Minute</key>
    <integer>${minute}</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/${slot}.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/${slot}.err.log</string>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
EOF

  launchctl bootout "gui/$(id -u)/${label}" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$plist"
  launchctl enable "gui/$(id -u)/${label}"
  echo "Installed ${label} (${hour}:$(printf '%02d' ${minute}) daily)"
}

if [[ ! -x "$PY" ]]; then
  echo "Run scripts/setup.sh first."
  exit 1
fi

install_plist "com.aimee.hrjobhunt.morning" "morning" 8 0
install_plist "com.aimee.hrjobhunt.evening" "evening" 20 0
install_plist "com.aimee.hrjobhunt.applied" "applied_summary" 20 5

LISTENER="$LAUNCH_DIR/com.aimee.hrjobhunt.listener.plist"
cat > "$LISTENER" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.aimee.hrjobhunt.listener</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PY}</string>
    <string>${ROOT}/src/bot_listener.py</string>
  </array>
  <key>KeepAlive</key>
  <true/>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/listener.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/listener.err.log</string>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/com.aimee.hrjobhunt.listener" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$LISTENER"
launchctl enable "gui/$(id -u)/com.aimee.hrjobhunt.listener"
echo "Installed com.aimee.hrjobhunt.listener (always-on instant replies)"

echo ""
echo "Schedule:"
echo "  08:00  Top 10 搵工 list"
echo "  20:00  Top 10 搵工 list"
echo "  20:05  已 apply 清單"
echo "  長駐   Bot listener（即時回覆）"
echo ""
echo "Done. Mac 要開機先收到 push（sleep 期間可能延遲）。"
echo "Logs: $LOG_DIR"
