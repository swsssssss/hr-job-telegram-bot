"""Send formatted job reminders via Telegram."""

from __future__ import annotations

import html
import re
from typing import List, Optional, Tuple

import requests

from src.date_utils import format_now_hkt, format_posted_label
from src.enrich_jobs import normalize_source
from src.fetch_jobs import Job

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MESSAGE_LEN = 4000
DEFAULT_DISPLAY_LIMIT = 10


def _job_block(idx: int, job: Job, reasons: List[str]) -> List[str]:
    title = html.escape(job.title)
    company = html.escape(job.company)
    location = html.escape(job.location or "—")
    url = html.escape(job.url)
    source = html.escape(normalize_source(job.url, job.source))
    lines = [
        f"<b>{idx}. {title}</b>",
        f"📌 {source} | 🏢 {company} | 📍 {location}",
    ]
    if job.posted_date:
        lines.append(f"🗓 {html.escape(format_posted_label(job.posted_date))}")
    if job.note:
        # Keep notes short so Top 10 stays within Telegram limits.
        note = job.note.strip()
        if len(note) > 140:
            note = note[:137] + "..."
        lines.append(f"💡 {html.escape(note)}")
    if reasons:
        display_reasons = [r for r in reasons if not r.startswith("Posted")]
        if display_reasons:
            lines.append(f"✅ {html.escape(', '.join(display_reasons[:2]))}")
    lines.append(f'👉 <a href="{url}">Apply link</a>')
    lines.append("")
    return lines


def build_message(
    ranked: List[Tuple[Job, int, List[str]]],
    slot_label: str,
    display_limit: int = DEFAULT_DISPLAY_LIMIT,
) -> str:
    now = format_now_hkt()
    total = len(ranked)
    shown = ranked[: max(display_limit, 0)] if display_limit > 0 else ranked
    shown_count = len(shown)

    if total == 0:
        list_heading = "<b>今日暫無符合條件嘅職位</b>"
    elif shown_count < total:
        list_heading = (
            f"<b>符合條件嘅職位（9 日內 post，共 {total} 個；顯示 Top {shown_count}）：</b>"
        )
    else:
        list_heading = f"<b>符合條件嘅職位（9 日內 post，共 {total} 個）：</b>"

    if slot_label == "朝早":
        title_line = "🕗 <b>朝早 08:00 HR 搵工提醒</b>"
    elif slot_label == "晚間":
        title_line = "🕗 <b>晚間 20:00 HR 搵工提醒</b>"
    else:
        title_line = f"🕗 <b>{html.escape(slot_label)} HR 搵工提醒</b>"

    lines = [
        title_line,
        f"📅 送出時間（香港）：{html.escape(now)}",
        "🔄 每次 send 都會重新 fetch 最新職位",
        "",
        list_heading,
        "",
    ]

    if not shown:
        lines.extend(
            [
                "今日未搵到新符合條件嘅工，",
                "請手動 check JobsDB / CTgoodjobs。",
                "",
            ]
        )
    else:
        for idx, (job, _score, reasons) in enumerate(shown, start=1):
            lines.extend(_job_block(idx, job, reasons))
        if shown_count < total:
            remaining = total - shown_count
            lines.append(
                f"➕ 其餘 {remaining} 個未顯示。回覆 <code>list</code> 可再睇最新清單。"
            )
            lines.append("")

    lines.extend(
        [
            "⏰ <b>記得今日申請未 apply 嘅職位！</b>",
            "📝 已 apply：回覆 <code>applied 1</code> 或 <code>applied kerry</code>",
            "💰 表格填 expected salary：<b>$32,000</b>",
            "🎯 面試底線：<b>$28,000</b>",
        ]
    )
    return "\n".join(lines)


def build_applied_message(applied_entries: list[dict]) -> str:
    now = format_now_hkt()
    lines = [
        "📋 <b>晚間已 Apply 清單</b>",
        f"📅 送出時間（香港）：{html.escape(now)}",
        "",
    ]

    if not applied_entries:
        lines.append("目前未有任何 apply 記錄。")
        lines.append("")
        lines.append("Apply 完可以回覆：<code>applied 1</code> 或 <code>applied 2 3</code>")
        return "\n".join(lines)

    lines.append(f"<b>共 {len(applied_entries)} 個已 apply 職位：</b>")
    lines.append("")

    for idx, entry in enumerate(applied_entries, start=1):
        title = html.escape(entry.get("title") or "Unknown role")
        company = html.escape(entry.get("company") or "—")
        url = html.escape(entry.get("url") or "")
        source = html.escape(normalize_source(entry.get("url", ""), ""))
        applied_at = entry.get("applied_at", "")
        applied_label = applied_at[:10] if applied_at else "—"

        lines.append(f"<b>{idx}. {title}</b>")
        lines.append(f"📌 {source} | 🏢 {company}")
        lines.append(f"🗓 Applied on {html.escape(applied_label)}")
        if url:
            lines.append(f'👉 <a href="{url}">Job link</a>')
        lines.append("")

    lines.append("取消記錄：<code>undo 1</code> 或 <code>undo https://...</code>")
    return "\n".join(lines)


def _close_open_html_tags(text: str) -> str:
    """Append closing tags for any still-open simple HTML tags."""
    open_tags: List[str] = []
    for match in re.finditer(r"</?([a-zA-Z]+)(?:\s[^>]*)?>", text):
        full = match.group(0)
        tag = match.group(1).lower()
        if full.startswith("</"):
            if open_tags and open_tags[-1] == tag:
                open_tags.pop()
            continue
        if full.endswith("/>"):
            continue
        open_tags.append(tag)
    for tag in reversed(open_tags):
        text += f"</{tag}>"
    return text


def truncate_telegram_html(text: str, max_len: int = MAX_MESSAGE_LEN) -> str:
    """Truncate without cutting mid-tag; keep Telegram HTML parseable."""
    if len(text) <= max_len:
        return text

    budget = max_len - len("\n...(truncated)")
    cut = text[:budget]
    # Prefer cutting at a blank line / job boundary.
    for separator in ("\n\n", "\n"):
        idx = cut.rfind(separator)
        if idx >= budget // 2:
            cut = cut[:idx]
            break

    # If we landed inside an unclosed HTML tag, drop the partial tag.
    last_lt = cut.rfind("<")
    last_gt = cut.rfind(">")
    if last_lt > last_gt:
        cut = cut[:last_lt].rstrip()

    return _close_open_html_tags(cut) + "\n...(truncated)"


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    text = truncate_telegram_html(text, MAX_MESSAGE_LEN)

    response = requests.post(
        TELEGRAM_API.format(token=token),
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error: {payload}")


def display_limit_from_config(config: Optional[dict]) -> int:
    if not config:
        return DEFAULT_DISPLAY_LIMIT
    criteria = config.get("criteria") or {}
    raw = criteria.get("telegram_list_limit", DEFAULT_DISPLAY_LIMIT)
    try:
        return max(int(raw), 1)
    except (TypeError, ValueError):
        return DEFAULT_DISPLAY_LIMIT
