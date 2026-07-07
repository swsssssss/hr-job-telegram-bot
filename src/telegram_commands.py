"""Process Telegram replies for the HR job bot."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional, Tuple

import requests

from src.applied_jobs import (
    load_applied,
    load_last_sent_jobs,
    mark_applied,
    mark_applied_by_company,
    mark_applied_by_rank,
    unmark_applied,
)
from src.job_service import build_applied_list_message, build_job_list_message

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
Reply = Tuple[str, str]  # (parse_mode, text)


def _state_path(root: Path) -> Path:
    return root / "data" / "telegram_state.json"


def _load_offset(root: Path) -> int:
    path = _state_path(root)
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as f:
        return int(json.load(f).get("update_offset", 0))


def _save_offset(root: Path, offset: int) -> None:
    path = _state_path(root)
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"update_offset": offset}, f)


def send_telegram_text(
    token: str,
    chat_id: str,
    text: str,
    parse_mode: Optional[str] = None,
) -> None:
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    response = requests.post(
        TELEGRAM_API.format(token=token, method="sendMessage"),
        json=payload,
        timeout=60,
    )
    response.raise_for_status()


def _help_message() -> Reply:
    text = "\n".join(
        [
            "📖 <b>Bot 指令</b>",
            "",
            "<b>Mark 已 apply</b>",
            "<code>applied 1</code> — Mark 最近一次 list 嘅 #1",
            "<code>applied 1 3</code> — Mark 多個編號",
            "<code>applied kerry</code> — Mark 公司名（例如 Kerry）",
            "<code>applied https://...</code> — Mark job link",
            "",
            "<b>查詢</b>",
            "<code>list</code> — 即時 Top 10（未 apply）",
            "<code>applied list</code> — 已 apply 清單",
            "",
            "<b>取消</b>",
            "<code>undo 1</code> — 取消 apply 記錄",
            "",
            "每日自動 send（香港時間）：08:00 / 20:00 Top 10，20:05 已 apply 清單",
        ]
    )
    return "HTML", text


def _extract_ranks(text: str) -> List[int]:
    lowered = text.lower().strip()
    for prefix in ("applied", "已apply", "已申請", "apply", "undo"):
        if lowered.startswith(prefix):
            lowered = lowered[len(prefix) :].strip(" :：")
            break
    else:
        return []
    return [int(n) for n in re.findall(r"\d+", lowered)]


def _extract_url(text: str) -> Optional[str]:
    match = re.search(r"https?://\S+", text.strip())
    return match.group(0).rstrip(".,)") if match else None


def _is_applied_command(text: str) -> bool:
    lowered = text.lower().strip()
    return any(token in lowered for token in ("applied", "已apply", "已申請", "apply"))


def _company_keyword_from_applied_command(text: str) -> Optional[str]:
    lowered = text.lower().strip()
    for prefix in ("applied", "已apply", "已申請"):
        if lowered.startswith(prefix):
            rest = lowered[len(prefix) :].strip(" :：")
            if rest and not rest[0].isdigit() and not rest.startswith("http"):
                return rest
    return None


def handle_text_command(text: str, root: Path) -> Optional[Reply]:
    lowered = text.lower().strip()

    if lowered in ("help", "/help", "/start", "指令", "幫助"):
        return _help_message()

    if lowered in ("list", "top10", "top 10", "搵工", "清單"):
        return "HTML", build_job_list_message(root, slot_label="即時")

    if lowered in ("applied list", "已apply list", "已申請 list", "appliedlist"):
        return "HTML", build_applied_list_message(root)

    if lowered.startswith("undo"):
        url = _extract_url(text)
        if url:
            removed = unmark_applied(root, url)
            msg = "已取消 apply 記錄。" if removed else "搵唔到呢個 apply 記錄。"
            return "HTML", msg

        removed_any = False
        for rank in _extract_ranks(text):
            for item in load_last_sent_jobs(root):
                if item.get("rank") == rank:
                    removed_any = unmark_applied(root, item["url"]) or removed_any
        msg = "已取消 apply 記錄。" if removed_any else "搵唔到呢個 apply 記錄。"
        return "HTML", msg

    company_keyword = _company_keyword_from_applied_command(text)
    if company_keyword and _is_applied_command(text) and not _extract_ranks(text):
        entry = mark_applied_by_company(root, company_keyword)
        if not entry:
            return "HTML", f"搵唔到公司「{company_keyword}」。試下用 list 睇編號，再 send applied 1"
        title = entry.get("title") or entry.get("url")
        return "HTML", f"已 mark apply ✅\n- {title}"

    ranks = _extract_ranks(text)
    if ranks and _is_applied_command(text):
        marked = mark_applied_by_rank(root, ranks)
        if not marked:
            return "HTML", "搵唔到對應 job。請先用 list 睇編號，例如：applied 1"
        titles = [entry.get("title") or entry.get("url") for entry in marked]
        body = "已 mark apply ✅\n" + "\n".join(f"- {title}" for title in titles)
        return "HTML", body

    url = _extract_url(text)
    if url and _is_applied_command(text):
        mark_applied(root, url)
        return "HTML", f"已 mark apply ✅\n{url}"

    if _is_applied_command(text):
        return "HTML", "用法：applied 1 / applied kerry / applied list\nSend help 睇全部指令"

    return None


def process_telegram_commands(
    token: str,
    chat_id: str,
    root: Path,
    long_poll_seconds: int = 0,
) -> List[str]:
    offset = _load_offset(root)
    response = requests.get(
        TELEGRAM_API.format(token=token, method="getUpdates"),
        params={"offset": offset, "timeout": long_poll_seconds},
        timeout=max(35, long_poll_seconds + 10),
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(payload)

    replies: List[str] = []
    for update in payload.get("result", []):
        offset = max(offset, update["update_id"] + 1)
        message = update.get("message") or update.get("edited_message")
        if not message:
            continue
        if str(message.get("chat", {}).get("id")) != str(chat_id):
            continue

        text = (message.get("text") or "").strip()
        if not text:
            continue

        reply = handle_text_command(text, root)
        if reply:
            parse_mode, body = reply
            send_telegram_text(token, chat_id, body, parse_mode=parse_mode)
            replies.append(body)

    _save_offset(root, offset)
    return replies
