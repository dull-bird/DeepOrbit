"""Zero-dependency Chinese/English natural-language datetime extraction.

Extract-style parsing (Vikunja Quick Add Magic pattern): time expressions are
stripped from the input text, the remainder is the task title. Returns a dict
with `text`, `date`, `time`, `recurrence`, `priority`, plus `matched` spans for
echo confirmation. Deterministic; no model calls. jionlp is an optional
enhancer tried last for uncovered Chinese phrasing.
"""

from __future__ import annotations

import datetime as dt
import re

WEEKDAYS_ZH = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
WEEKDAYS_EN = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
CN_DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _cn_num(text: str) -> int | None:
    if text.isdigit():
        return int(text)
    if text in CN_DIGITS:
        return CN_DIGITS[text]
    match = re.fullmatch(r"十([一二三四五六七八九])?", text)
    if match:
        return 10 + (CN_DIGITS[match.group(1)] if match.group(1) else 0)
    match = re.fullmatch(r"([一二三四五六七八九])十([一二三四五六七八九])?", text)
    if match:
        return CN_DIGITS[match.group(1)] * 10 + (CN_DIGITS[match.group(2)] if match.group(2) else 0)
    return None


def _hm(hour: int, minute: int, period: str | None) -> tuple[int, int] | None:
    if period in ("下午", "晚上", "今晚", "明晚", "傍晚") and hour < 12:
        hour += 12
    elif period == "中午" and hour < 11:
        hour += 12
    elif period in ("凌晨",) and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute


def parse(text: str, *, now: dt.datetime | None = None) -> dict:
    """Extract date/time/recurrence/priority from free text. Never raises."""
    now = now or dt.datetime.now()
    today = now.date()
    result: dict = {"text": text.strip(), "date": None, "time": None, "recurrence": None, "priority": None, "matched": []}
    spans: list[tuple[int, int]] = []

    def claim(match: re.Match, **fields) -> None:
        spans.append(match.span())
        for key, value in fields.items():
            if value is not None and result.get(key) in (None, ""):
                result[key] = value

    def sub(pattern: str, handler, flags: int = 0) -> None:
        for match in re.finditer(pattern, text, flags):
            if any(s <= match.start() < e or s < match.end() <= e for s, e in spans):
                continue
            handler(match)

    # --- priority shorthands -------------------------------------------------
    sub(r"!([123])(?!\d)", lambda m: claim(m, priority={1: "high", 2: "medium", 3: "low"}[int(m.group(1))]))

    # --- ISO ------------------------------------------------------------------
    sub(r"(?P<d>\d{4}-\d{2}-\d{2})[T ](?P<t>\d{1,2}:\d{2})", lambda m: claim(m, date=m.group("d"), time=m.group("t")))
    sub(r"(?<![\d-])(?P<d>\d{4}-\d{2}-\d{2})(?![\d:])", lambda m: claim(m, date=m.group("d")))

    # --- recurrence (before one-shot weekday patterns) ------------------------
    def recur_zh(m: re.Match) -> None:
        unit = m.group("unit")
        wd = m.group("wd")
        if wd or unit == "周":
            if wd:
                day = WEEKDAYS_ZH[wd]
                name = list(WEEKDAYS_EN)[day]
                claim(m, recurrence=f"every week on {name}", date=_next_weekday(today, day).isoformat())
            else:
                claim(m, recurrence="every week", date=today.isoformat())
        elif unit in ("天", "日"):
            claim(m, recurrence="every day", date=today.isoformat())
        else:
            claim(m, recurrence="every month", date=today.isoformat())

    sub(r"每(?P<unit>天|日|周|个月|月)(?P<wd>[一二三四五六日天])?", recur_zh)
    sub(r"每隔(?P<n>\d+)[天日]", lambda m: claim(m, recurrence=f"every {m.group('n')} days", date=today.isoformat()))
    sub(r"\bevery\s+(?P<wd>monday|tuesday|wednesday|thursday|friday|saturday|sunday)s?\b",
        lambda m: claim(m, recurrence=f"every week on {m.group('wd')}", date=_next_weekday(today, WEEKDAYS_EN[m.group("wd")]).isoformat()), re.I)
    sub(r"\bevery\s+(?P<unit>day|week|month)\b",
        lambda m: claim(m, recurrence=f"every {m.group('unit').lower()}", date=today.isoformat()), re.I)
    sub(r"\bevery\s+(?P<n>\d+)\s+days?\b", lambda m: claim(m, recurrence=f"every {m.group('n')} days", date=today.isoformat()), re.I)

    # --- relative day words + optional clock -----------------------------------
    DAY_WORDS = {"今天": 0, "今日": 0, "今晚": 0, "明早": 1, "明天": 1, "明晚": 1, "后天": 2, "大后天": 3}

    def zh_day(m: re.Match) -> None:
        offset = DAY_WORDS[m.group("word")]
        date = today + dt.timedelta(days=offset)
        hour, minute = 0, 0
        period = m.group("period") or ("晚上" if m.group("word") in ("今晚", "明晚") else "上午" if m.group("word") == "明早" else None)
        hm = None
        if m.group("clock"):
            hm = _parse_clock(m.group("clock"), period)
        claim(m, date=date.isoformat(), time=f"{hm[0]:02d}:{hm[1]:02d}" if hm else None)

    sub(r"(?P<word>今天|今日|今晚|明早|明天|明晚|后天|大后天)\s*(?P<period>上午|早上|早晨|中午|下午|傍晚|晚上|凌晨)?\s*(?P<clock>[0-9一二两三四五六七八九十]{1,3}点(?:半|[0-9一二三四五六七八九十]{1,2}分?)?)?", zh_day)

    def en_day(m: re.Match) -> None:
        word = m.group("word").lower()
        offset = 0 if word in ("today", "tonight") else 1
        hm = _parse_en_clock(m.group("clock"), 19 if word == "tonight" and not m.group("clock") else None)
        claim(m, date=(today + dt.timedelta(days=offset)).isoformat(), time=hm)

    sub(r"\b(?P<word>today|tonight|tomorrow)\b\s*(?P<clock>(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?", en_day, re.I)

    # --- standalone clock with period (date = today) ---------------------------
    def zh_clock(m: re.Match) -> None:
        hm = _parse_clock(m.group("clock"), m.group("period"))
        if hm:
            claim(m, date=today.isoformat(), time=f"{hm[0]:02d}:{hm[1]:02d}")

    sub(r"(?P<period>上午|早上|早晨|中午|下午|傍晚|晚上|凌晨)\s*(?P<clock>[0-9一二两三四五六七八九十]{1,3}点(?:半|[0-9一二三四五六七八九十]{1,2}分?)?)", zh_clock)

    # --- weekday references ------------------------------------------------------
    sub(r"下(?:周|星期)(?P<wd>[一二三四五六日天])",
        lambda m: claim(m, date=_next_weekday(today, WEEKDAYS_ZH[m.group("wd")], weeks=1).isoformat()))
    sub(r"(?:这?周|星期)(?P<wd>[一二三四五六日天])",
        lambda m: claim(m, date=_next_weekday(today, WEEKDAYS_ZH[m.group("wd")]).isoformat()))
    sub(r"\bnext\s+(?P<wd>monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        lambda m: claim(m, date=_next_weekday(today, WEEKDAYS_EN[m.group("wd").lower()], weeks=1).isoformat()), re.I)
    sub(r"\bon\s+(?P<wd>monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        lambda m: claim(m, date=_next_weekday(today, WEEKDAYS_EN[m.group("wd").lower()]).isoformat()), re.I)

    # --- N units later -----------------------------------------------------------
    UNIT_DAYS = {"天": "days", "日": "days", "周": "weeks", "星期": "weeks", "个月": "months", "月": "months"}

    def zh_later(m: re.Match) -> None:
        n = _cn_num(m.group("n")) or 0
        unit = UNIT_DAYS[m.group("unit")]
        if unit == "days":
            date = today + dt.timedelta(days=n)
        elif unit == "weeks":
            date = today + dt.timedelta(weeks=n)
        else:
            month = today.month - 1 + n
            date = dt.date(today.year + month // 12, month % 12 + 1, min(today.day, 28))
        claim(m, date=date.isoformat())

    CN = "0-9一二两三四五六七八九十"
    sub(rf"(?P<n>[{CN}]+)\s*(?P<unit>天|日|周|星期|个月|月)后", zh_later)
    sub(rf"(?P<n>[{CN}]+)\s*小时后", lambda m: claim(m, date=today.isoformat(), time=(now + dt.timedelta(hours=_cn_num(m.group("n")) or 0)).strftime("%H:%M")))
    sub(rf"(?P<n>[{CN}]+)\s*分钟后", lambda m: claim(m, date=today.isoformat(), time=(now + dt.timedelta(minutes=_cn_num(m.group("n")) or 0)).strftime("%H:%M")))
    def en_later(m: re.Match) -> None:
        n = int(m.group("n"))
        unit = m.group("unit").lower().rstrip("s")
        days = n if unit == "day" else 7 * n if unit == "week" else 30 * n
        claim(m, date=(today + dt.timedelta(days=days)).isoformat())

    sub(r"\bin\s+(?P<n>\d+)\s+(?P<unit>days?|weeks?|months?)\b", en_later, re.I)
    sub(r"\bin\s+(?P<n>\d+)\s+hours?\b", lambda m: claim(m, date=today.isoformat(), time=(now + dt.timedelta(hours=int(m.group("n")))).strftime("%H:%M")), re.I)

    # --- Chinese month/day --------------------------------------------------------
    def zh_md(m: re.Match) -> None:
        month, day = int(m.group("mo")), int(m.group("d"))
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return
        date = dt.date(today.year, month, day)
        if date < today:
            date = dt.date(today.year + 1, month, day)
        claim(m, date=date.isoformat())

    sub(r"(?P<mo>\d{1,2})月(?P<d>\d{1,2})[日号]", zh_md)

    # --- clock-only HH:MM ------------------------------------------------------------
    sub(r"(?<![\d:])(?P<t>[01]?\d|2[0-3]):(?P<mm>[0-5]\d)(?![\d:])", lambda m: claim(m, date=today.isoformat(), time=f"{int(m.group('t')):02d}:{m.group('mm')}"))
    sub(r"\b(?P<h>[1-9]|1[0-2])\s*(?P<ampm>am|pm)\b",
        lambda m: claim(m, date=today.isoformat(), time=f"{(int(m.group('h')) % 12) + (12 if m.group('ampm').lower() == 'pm' else 0):02d}:00"), re.I)

    # strip claimed spans from the title
    pieces: list[str] = []
    cursor = 0
    for start, end in sorted(spans):
        pieces.append(text[cursor:start])
        cursor = max(cursor, end)
    pieces.append(text[cursor:])
    result["text"] = re.sub(r"\s+", " ", " ".join(pieces)).strip(" ，,。")
    result["matched"] = [text[s:e] for s, e in sorted(spans)]
    return result


def _next_weekday(today: dt.date, weekday: int, *, weeks: int = 0) -> dt.date:
    """weeks=0: 最近一次（今天可命中）；weeks=1: 下周的该天（至少 +7）。"""
    return today + dt.timedelta(days=(weekday - today.weekday()) % 7 + weeks * 7)


def _parse_clock(clock: str | None, period: str | None) -> tuple[int, int] | None:
    if not clock:
        return None
    match = re.fullmatch(r"([0-9一二两三四五六七八九十]{1,3})点(?:(半)|([0-9一二三四五六七八九十]{1,2})分?)?", clock)
    if not match:
        return None
    hour = _cn_num(match.group(1))
    if hour is None:
        return None
    minute = 30 if match.group(2) else (_cn_num(match.group(3)) if match.group(3) else 0)
    if minute is None:
        return None
    return _hm(hour, minute, period)


def _parse_en_clock(clock: str | None, default_hour: int | None) -> str | None:
    if not clock or not clock.strip():
        return f"{default_hour:02d}:00" if default_hour else None
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", clock, re.I)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    ampm = (match.group(3) or "").lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return f"{hour:02d}:{minute:02d}"
