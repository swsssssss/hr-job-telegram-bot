#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MESSAGE="${1:-Update bot data [skip ci]}"

git config user.name "hr-job-bot"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

mkdir -p data

for file in applied_jobs.json telegram_state.json cache.json last_sent_slots.json; do
  if [[ ! -f "data/$file" ]]; then
    case "$file" in
      applied_jobs.json) echo "{}" > "data/$file" ;;
      telegram_state.json) echo '{"update_offset": 0}' > "data/$file" ;;
    esac
  fi
done

files=()
for file in applied_jobs.json telegram_state.json cache.json last_sent_slots.json; do
  if [[ -f "data/$file" ]]; then
    files+=("data/$file")
  fi
done

if [[ ${#files[@]} -eq 0 ]]; then
  echo "No bot data files to commit."
  exit 0
fi

git add "${files[@]}"

if git diff --staged --quiet; then
  echo "No bot data changes to commit."
  exit 0
fi

git commit -m "$MESSAGE"
git push
