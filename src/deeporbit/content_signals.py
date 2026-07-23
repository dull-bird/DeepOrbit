"""Content-aware signals for privacy scoring.

This module provides heuristic detectors that distinguish *personal sensitive
data* from *public content that merely discusses sensitive topics*.  All
functions are pure-Python with zero external dependencies.

Layers provided:
- length_factor: density normalisation for long documents
- detect_source_signals: external/public content detection (source_factor)
- detect_voice_signals: first-person intimate writing detection (voice_factor)
- filename_signal: filename-only keyword sensitivity (capped ±3)
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Layer 2: Length attenuation
# ---------------------------------------------------------------------------


def length_factor(char_count: int) -> float:
    """Attenuate keyword density for long documents.

    A 200-char diary entry keeps full weight; a 10 000-char paper is reduced
    to 30 %.
    """
    if char_count <= 500:
        return 1.0
    if char_count <= 2000:
        return 0.85
    if char_count <= 5000:
        return 0.65
    if char_count <= 15000:
        return 0.45
    return 0.30


# ---------------------------------------------------------------------------
# Layer 3: Source / public-content detection
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r"https?://[^\s\)\]>\"']+" )
_ACADEMIC_RE = re.compile(
    r"(?i)(参考文献|references|bibliography|doi\.org|arxiv\.org|issn|isbn|\barXiv\b)",
)
_TRANSLATION_RE = re.compile(
    r"(?i)(翻译|translated?\b|译者|translation|译自)",
)
# Transcript format: timestamps like 00:00 or 1:23:45 combined with speaker labels
_TRANSCRIPT_TS_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
_TRANSCRIPT_SPEAKER_RE = re.compile(r"\*\*[^*]{1,40}:\*\*|^[A-Z][a-z]+ [A-Z][a-z]+:", re.MULTILINE)
# Personal identity markers that invalidate table-based source detection
_PERSONAL_TABLE_RE = re.compile(
    r"姓名|住院号|病历号|患者|病人|身份证|报告号|临床诊断|检查报告|年龄.*岁",
)


def _count_table_rows(text: str) -> int:
    """Count consecutive Markdown table rows (lines starting with |)."""
    max_run = 0
    run = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            run += 1
            if run > max_run:
                max_run = run
        else:
            run = 0
    return max_run


def detect_source_signals(text: str, fields: dict[str, str]) -> float:
    """Return a source_factor in (0, 1].

    Lower values mean stronger evidence that the file is public/external
    content.  Multiple signals: take the strongest (lowest factor), do NOT
    stack multiplicatively.
    """
    factors: list[float] = []

    # Frontmatter has explicit source field
    if fields.get("source"):
        factors.append(0.3)

    # Frontmatter type indicates external content
    ftype = fields.get("type", "").lower()
    if ftype in ("note", "paper", "transcript", "podcast", "video"):
        factors.append(0.4)

    # >= 3 URLs in body
    url_count = len(_URL_RE.findall(text))
    if url_count >= 3:
        factors.append(0.5)
    elif url_count >= 1:
        factors.append(0.7)

    # Academic markers
    if _ACADEMIC_RE.search(text):
        factors.append(0.4)

    # Translation markers
    if _TRANSLATION_RE.search(text):
        factors.append(0.5)

    # Transcript format (timestamps + speaker labels)
    ts_matches = _TRANSCRIPT_TS_RE.findall(text)
    if len(ts_matches) >= 5 and _TRANSCRIPT_SPEAKER_RE.search(text):
        factors.append(0.4)

    # Dense table data (>= 10 consecutive table rows)
    # BUT: tables containing personal identity markers are NOT public reference
    if _count_table_rows(text) >= 10:
        if not _PERSONAL_TABLE_RE.search(text):
            factors.append(0.5)

    if not factors:
        return 1.0
    return min(factors)


# ---------------------------------------------------------------------------
# Layer 4: Voice / intimacy detection
# ---------------------------------------------------------------------------

_FIRST_PERSON_EMOTION_RE = re.compile(
    r"我[很太真有点]*"
    r"(焦虑|害怕|担心|难过|伤心|开心|高兴|紧张|疲惫|累|崩溃|无助|孤独|愤怒|委屈|迷茫|压力)"
    r"|我感到|我觉得[很太]|我今天[很太]|我最近[很太]",
)
_DATE_EVENT_RE = re.compile(
    r"\d{1,2}月\d{1,2}日|"
    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|"
    r"(?:今天|昨天|前天|上周|这周)",
)
_NAMED_PERSON_ACTION_RE = re.compile(
    r"(?:母亲|父亲|妈妈|爸爸|老婆|老公|妻子|丈夫|儿子|女儿|孩子)"
    r"(?:今天|昨天|现在|最近|说|问|去|来|打电话|住院|检查|手术)",
)


def detect_voice_signals(text: str, fields: dict[str, str]) -> float:
    """Return a voice_factor in [1.0, 1.5].

    Higher values mean stronger evidence of first-person intimate writing.
    Multiple signals: take the strongest, capped at 1.5.
    """
    factors: list[float] = []

    # First-person emotional expressions (>= 3 occurrences)
    emotion_count = len(_FIRST_PERSON_EMOTION_RE.findall(text))
    if emotion_count >= 3:
        factors.append(1.3)
    elif emotion_count >= 1:
        factors.append(1.1)

    # Specific date + event combinations
    date_count = len(_DATE_EVENT_RE.findall(text))
    if date_count >= 3:
        factors.append(1.2)
    elif date_count >= 1:
        factors.append(1.1)

    # Named family member + action
    if _NAMED_PERSON_ACTION_RE.search(text):
        factors.append(1.2)

    # Diary-type frontmatter
    ftype = fields.get("type", "").lower()
    if ftype in ("diary", "daily", "journal"):
        factors.append(1.2)
    # Date in frontmatter suggests personal log
    if fields.get("date") and re.match(r"\d{4}-\d{2}-\d{2}", fields.get("date", "")):
        if ftype not in ("note", "paper", "transcript"):
            factors.append(1.1)

    if not factors:
        return 1.0
    return min(max(factors), 1.5)


# ---------------------------------------------------------------------------
# Filename signal (replaces directory-based path scoring)
# ---------------------------------------------------------------------------

_FILENAME_SENSITIVE: dict[str, int] = {
    "简历": 3,
    "resume": 3,
    "身份证": 3,
    "病历": 3,
    "密码": 3,
    "password": 3,
    "母亲": 2,
    "父亲": 2,
    "妈妈": 2,
    "爸爸": 2,
    "家人": 2,
    "医疗": 2,
    "面试": 2,
    "求职": 2,
    "跳槽": 2,
    "offer": 2,
    "离职": 2,
    "背调": 2,
    "体检": 2,
    "诊断": 2,
    "合同": 2,
    "诉讼": 2,
    "仲裁": 2,
    "cv": 2,
}


def filename_signal(filename: str) -> int:
    """Return a filename-based sensitivity bonus, capped at [-3, +3].

    Only the filename (not directory) is considered — it is content metadata.
    """
    lower = filename.lower().removesuffix(".md")
    total = 0
    for keyword, weight in _FILENAME_SENSITIVE.items():
        if keyword in lower:
            total += weight
    return max(-3, min(3, total))


# ---------------------------------------------------------------------------
# Excerpt extraction for LLM verification
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？\.\!\?\n])")


def extract_sensitive_excerpt(
    text: str,
    keywords: list[str],
    *,
    max_chars: int = 800,
    max_snippets: int = 6,
) -> str:
    """Extract the most privacy-relevant snippets from a document.

    Strategy:
    1. Split text into sentences.
    2. Score each sentence by how many privacy keywords it contains.
    3. Return top-N sentences (capped by max_chars) joined together.

    This gives an LLM verifier the densest signal in the smallest payload.
    """
    # Strip frontmatter
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            body = text[end + 4:]

    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(body) if s.strip()]
    if not sentences:
        return body[:max_chars]

    # Score sentences by keyword density
    scored: list[tuple[int, str]] = []
    for sent in sentences:
        hits = sum(1 for kw in keywords if kw in sent)
        if hits > 0:
            scored.append((hits, sent))

    # Sort by hits desc, take top snippets
    scored.sort(key=lambda x: -x[0])
    snippets: list[str] = []
    total = 0
    for _, sent in scored[:max_snippets]:
        if total + len(sent) > max_chars:
            break
        snippets.append(sent)
        total += len(sent)

    if not snippets:
        # No keyword hits — fall back to opening text
        return body[:max_chars]
    return "\n".join(snippets)
