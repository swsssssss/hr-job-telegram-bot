"""Send formatted job reminders via Telegram."""

from __future__ import annotations

import html
from typing import List, Tuple

import requests

from src.date_utils import format_now_hkt, format_posted_label
from src.enrich_jobs import normalize_source
from src.fetch_jobs import Job

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MESSAGE_LEN = 4000


def build_message(
    ranked: List[Tuple[Job, int, List[str]]],
    slot_label: str,
) -> str:
    now = format_now_hkt()
    count = len(ranked)
    if count == 0:
        list_heading = "<b>今日暫無符合條件嘅職位</b>"
    else:
        list_heading = f"<b>符合條件嘅職位（9 日內 post，共 {count} 個）：</b>"

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

    if not ranked:
        lines.extend(
            [
                "今日未搵到新符合條件嘅工，",
                "請手動 check JobsDB / CTgoodjobs。",
                "",
            ]
        )
    else:
        for idx, (job, _score, reasons) in enumerate(ranked, start=1):
            title = html.escape(job.title)
            company = html.escape(job.company)
            location = html.escape(job.location or "—")
            url = html.escape(job.url)
            source = html.escape(normalize_source(job.url, job.source))
            lines.append(f"<b>{idx}. {title}</b>")
            lines.append(f"📌 {source} | 🏢 {company} | 📍 {location}")
            if job.posted_date:
                lines.append(f"🗓 {html.escape(format_posted_label(job.posted_date))}")
            if job.note:
                lines.append(f"💡 {html.escape(job.note)}")
            if reasons:
                # Skip duplicate posted-date reason; show other match reasons only
                display_reasons = [r for r in reasons if not r.startswith("Posted")]
                if display_reasons:
                    lines.append(f"✅ {html.escape(', '.join(display_reasons[:2]))}")
            lines.append(f'👉 <a href="{url}">Apply link</a>')
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


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    if len(text) > MAX_MESSAGE_LEN:
        text = text[: MAX_MESSAGE_LEN - 20] + "\n...(truncated)"

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
