from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Protocol, runtime_checkable

from .content_signals import (
    detect_source_signals,
    detect_voice_signals,
    filename_signal,
    length_factor,
)
from .frontmatter import read_fields

PrivacyLevel = Literal["low", "medium", "high", "critical"]

LEVELS: list[PrivacyLevel] = ["low", "medium", "high", "critical"]

# Maximum contribution from any single keyword category (Layer 1).
CATEGORY_CAP = 6

DEFAULT_THRESHOLDS: dict[PrivacyLevel, int] = {
    "low": 0,
    "medium": 4,
    "high": 8,
    "critical": 12,
}

# Path-based privacy hints: matched path segments add weight to the base score.
PATH_SENSITIVITY: dict[str, int] = {
    "简历": 4,
    "resume": 4,
    "cv": 3,
    "面试": 3,
    "interview": 3,
    "求职": 3,
    "job": 3,
    "offer": 3,
    "工作经历": 4,
    "work experience": 4,
    "家庭": 3,
    "family": 3,
    "母亲": 3,
    "父亲": 3,
    "医疗": 3,
    "medical": 3,
    "医院": 3,
    "hospital": 3,
    "病历": 4,
    "profile": 2,
    "档案": 3,
    "身份证": 5,
    "secret": 2,
    "密码": 4,
    "password": 4,
}

# Category weight -> each keyword match in that category adds the weight.
PRIVACY_CATEGORIES: dict[str, tuple[int, list[str]]] = {
    "identity": (
        2,
        [
            "身份证",
            "身份证号",
            "护照",
            "姓名",
            "出生日期",
            "出生年月",
            "籍贯",
            "户籍",
            "民族",
            "性别",
            "年龄",
            "id card",
            "passport",
            "date of birth",
            "nationality",
            "citizenship",
            "full name",
        ],
    ),
    "contact": (
        1,
        [
            "电话",
            "手机",
            "手机号",
            "邮箱",
            "电子邮件",
            "微信",
            "微信号",
            "qq",
            "qq号",
            "地址",
            "住址",
            "收件地址",
            "紧急联系人",
            "wechat",
            "address",
            "contact",
            "reachable at",
            "mobile",
        ],
    ),
    "finance": (
        1,
        [
            "银行卡",
            "信用卡",
            "支付宝",
            "微信支付",
            "余额",
            "收入",
            "工资",
            "薪资",
            "年薪",
            "月薪",
            "股票账户",
            "证券",
            "基金",
            "salary",
            "income",
            "bonus",
            "stock option",
        ],
    ),
    "employment": (
        1,
        [
            "简历",
            "工作经历",
            "面试",
            "offer",
            "入职",
            "离职",
            "交接",
            "绩效",
            "年终奖",
            "跳槽",
            "背调",
            "推荐信",
            "reference letter",
            "employment",
            "resignation",
            "performance review",
            "job offer",
            "interview",
            "work experience",
        ],
    ),
    "health": (
        2,
        [
            "病历",
            "诊断",
            "医疗",
            "医院",
            "体检",
            "药物",
            "化疗",
            "癌症",
            "肿瘤",
            "检查报告",
            "病理",
            "处方",
            "医保",
            "病史",
            "medical record",
            "diagnosis",
            "hospital",
            "prescription",
            "insurance",
            "treatment",
            "chemotherapy",
        ],
    ),
    "family": (
        1,
        [
            "母亲",
            "父亲",
            "妻子",
            "丈夫",
            "孩子",
            "儿子",
            "女儿",
            "家庭",
            "家属",
            "亲人",
            "配偶",
            "长辈",
            "family",
            "mother",
            "father",
            "wife",
            "husband",
            "children",
            "son",
            "daughter",
            "spouse",
            "parent",
        ],
    ),
    "credentials": (
        2,
        [
            "密码",
            "密钥",
            "私钥",
            "password",
            "private key",
            "github token",
            "openai key",
        ],
    ),
    "mental": (
        1,
        [
            "情绪",
            "心理",
            "抑郁",
            "焦虑",
            "心理咨询",
            "精神",
            "自杀",
            "自残",
            "创伤",
            "mental health",
            "depression",
            "anxiety",
            "therapy",
            "psychologist",
            "suicide",
            "self-harm",
            "trauma",
        ],
    ),
    "legal": (
        1,
        [
            "律师",
            "合同",
            "诉讼",
            "仲裁",
            "赔偿",
            "纠纷",
            "官司",
            "劳动仲裁",
            "legal",
            "lawyer",
            "contract",
            "lawsuit",
            "arbitration",
            "compensation",
            "dispute",
        ],
    ),
    "relationships": (
        1,
        [
            "恋爱",
            "分手",
            "婚外情",
            "感情",
            "婚姻",
            "出轨",
            "relationship",
            "breakup",
            "affair",
            "marriage",
            "divorce",
        ],
    ),
    "biometric": (
        2,
        [
            "指纹",
            "人脸",
            "虹膜",
            "声纹",
            "人脸识别",
            "生物识别",
            "fingerprint",
            "face id",
            "biometric",
            "facial recognition",
        ],
    ),
}

# Pre-compile keyword regexes: keyword -> (weight, compiled regex).
# CJK keywords match anywhere (Chinese has no whitespace word boundaries);
# ASCII keywords use word-boundary lookarounds to avoid partial matches.
_KEYWORD_RE: dict[str, tuple[int, re.Pattern[str]]] = {}
for _category, (_weight, _keywords) in PRIVACY_CATEGORIES.items():
    for _kw in _keywords:
        if any("\u4e00" <= ch <= "\u9fff" for ch in _kw):
            # CJK keyword: no lookaround needed
            _pattern = re.compile(re.escape(_kw))
        else:
            # ASCII keyword: word-boundary lookaround
            _pattern = re.compile(rf"(?i)(?<!\w){re.escape(_kw)}(?!\w)")
        _KEYWORD_RE[_kw] = (_weight, _pattern)

PRIVACY_PATTERNS: dict[str, tuple[re.Pattern[str], int]] = {
    "id_number": (re.compile(r"\b\d{17}[\dXx]\b"), 3),
    "phone": (
        re.compile(
            r"\b(?:\+\d{1,3}[\s.-]+)?(?:\(?\d{2,4}\)?[\s.-]+)?\d{3,4}[\s.-]\d{4}\b"
        ),
        2,
    ),
    "email": (
        re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
        2,
    ),
    "secret": (
        re.compile(
            r"\b(?:sk-[A-Za-z0-9]{16,}|"
            r"ghp_[A-Za-z0-9]{20,}|"
            r"xox[baprs]-[A-Za-z0-9-]{10,}|"
            r"AKIA[0-9A-Z]{16})\b"
        ),
        3,
    ),
}


@dataclass(slots=True)
class PrivacyScore:
    path: str
    score: int = 0
    level: PrivacyLevel = "low"
    categories: dict[str, int] = field(default_factory=dict)
    patterns: dict[str, int] = field(default_factory=dict)
    existing_level: PrivacyLevel | None = None
    # Debugging / explain fields (v2 pipeline)
    raw_score: int = 0
    source_factor: float = 1.0
    voice_factor: float = 1.0
    length_factor: float = 1.0
    filename_signal: int = 0


def _filename_score(path: str) -> int:
    """Filename-only sensitivity signal (capped ±3). Directory is ignored."""
    name = Path(path).name
    return filename_signal(name)


def _score_text(text: str, category_cap: int = CATEGORY_CAP) -> dict[str, Any]:
    """Return score breakdown for a raw text string.

    Layer 1 (category cap) is applied here: each category's contribution is
    clamped to *category_cap* to prevent a single topic from dominating.
    """
    categories: dict[str, int] = {}
    patterns: dict[str, int] = {}
    total = 0

    for kw, (weight, pattern) in _KEYWORD_RE.items():
        count = len(pattern.findall(text))
        if count:
            for category, (cw, kws) in PRIVACY_CATEGORIES.items():
                if kw in kws:
                    categories[category] = categories.get(category, 0) + count * weight
                    break
            total += count * weight

    for name, (pattern, weight) in PRIVACY_PATTERNS.items():
        count = len(pattern.findall(text))
        if count:
            patterns[name] = count
            total += count * weight

    # Apply category cap: recompute total from capped categories + patterns.
    capped_total = 0
    for cat, val in categories.items():
        categories[cat] = min(val, category_cap)
        capped_total += categories[cat]
    for name, count in patterns.items():
        _, weight = PRIVACY_PATTERNS[name]
        capped_total += count * weight

    return {
        "score": capped_total,
        "raw_score": total,
        "categories": categories,
        "patterns": patterns,
    }


def _score_file(path: str, text: str, fields: dict[str, str] | None = None) -> dict[str, Any]:
    """Return score breakdown using the full 5-layer pipeline.

    Layers:
      1. Category cap (applied inside _score_text)
      2. Length attenuation
      3. Source/public-content detection
      4. Voice/intimacy detection
      5. Filename signal (additive)
    """
    breakdown = _score_text(text)
    base = breakdown["score"]

    lf = length_factor(len(text))
    sf = detect_source_signals(text, fields or {})
    vf = detect_voice_signals(text, fields or {})
    fn = _filename_score(path)

    final = int(round(base * lf * sf * vf)) + fn
    final = max(0, final)

    breakdown["score"] = final
    breakdown["length_factor"] = lf
    breakdown["source_factor"] = sf
    breakdown["voice_factor"] = vf
    breakdown["filename_signal"] = fn
    return breakdown


def level_for_score(score: int, thresholds: dict[PrivacyLevel, int] | None = None) -> PrivacyLevel:
    thresholds = thresholds or DEFAULT_THRESHOLDS
    if score >= thresholds["critical"]:
        return "critical"
    if score >= thresholds["high"]:
        return "high"
    if score >= thresholds["medium"]:
        return "medium"
    return "low"


def score_text(text: str, thresholds: dict[PrivacyLevel, int] | None = None) -> PrivacyScore:
    breakdown = _score_text(text)
    level = level_for_score(breakdown["score"], thresholds)
    return PrivacyScore(
        path="",
        score=breakdown["score"],
        level=level,
        categories=breakdown["categories"],
        patterns=breakdown["patterns"],
        raw_score=breakdown.get("raw_score", breakdown["score"]),
    )


def scan_file(
    path: Path,
    thresholds: dict[PrivacyLevel, int] | None = None,
    *,
    verifier: "Verifier | None" = None,
) -> PrivacyScore:
    text = path.read_text(encoding="utf-8", errors="ignore")
    fields = read_fields(text)
    existing_level = fields.get("privacy_level")
    if existing_level in LEVELS:
        existing_level = existing_level  # type: ignore[assignment]
    else:
        existing_level = None
    breakdown = _score_file(str(path), text, fields)
    level = level_for_score(breakdown["score"], thresholds)

    # Layer 5: optional LLM verification for gray-zone scores.
    if verifier is not None:
        th = thresholds or DEFAULT_THRESHOLDS
        gray_low = th["high"] - 2
        gray_high = th["critical"] + 2
        if gray_low <= breakdown["score"] <= gray_high:
            excerpt = text[:2000]
            adjusted = verifier.verify(str(path), excerpt, breakdown["score"], breakdown["categories"])
            if adjusted in LEVELS:
                level = adjusted  # type: ignore[assignment]

    score = PrivacyScore(
        path=str(path),
        score=breakdown["score"],
        level=level,
        categories=breakdown["categories"],
        patterns=breakdown["patterns"],
        existing_level=existing_level,  # type: ignore[arg-type]
        raw_score=breakdown.get("raw_score", breakdown["score"]),
        source_factor=breakdown.get("source_factor", 1.0),
        voice_factor=breakdown.get("voice_factor", 1.0),
        length_factor=breakdown.get("length_factor", 1.0),
        filename_signal=breakdown.get("filename_signal", 0),
    )
    return score


def scan_vault(
    vault: Path,
    index_dirs: list[str] | None = None,
    thresholds: dict[PrivacyLevel, int] | None = None,
    *,
    exclude_dirs: list[str] | None = None,
    include_system: bool = True,
) -> Iterable[PrivacyScore]:
    dirs = index_dirs or [
        "00_Inbox",
        "10_Diary",
        "15_Writings",
        "20_Projects",
        "30_Research",
        "40_Wiki",
        "50_Resources",
        "60_Notes",
        "70_Family",
        "90_Plans",
    ]
    if include_system:
        dirs = [*dirs, "99_System"]
    exclude = [Path(p) for p in (exclude_dirs or [])]
    for d in dirs:
        dir_path = vault / d
        if not dir_path.exists():
            continue
        for md in sorted(dir_path.rglob("*.md")):
            if md.name.startswith("."):
                continue
            try:
                rel = md.relative_to(vault)
            except ValueError:
                continue
            if any(ex in rel.parents or rel == ex for ex in exclude):
                continue
            if any(part in ("微信读书", "weread", "node_modules", ".obsidian") for part in rel.parts):
                continue
            yield scan_file(md, thresholds)


def effective_mode(
    file_level: PrivacyLevel,
    command_mode: str | None,
    enforce: dict[PrivacyLevel, str] | None = None,
) -> str:
    """Determine the effective privacy mode for a file.

    The enforcement table defines what happens to a file of a given level
    when it is exported. The command-level override (`command_mode`) can
    only make the policy stricter, never looser, except for explicit `allow`.
    """
    enforce = enforce or {
        "low": "allow",
        "medium": "allow",
        "high": "redact",
        "critical": "block",
    }
    base = enforce.get(file_level, "allow")
    if command_mode is None:
        return base
    if command_mode == "allow":
        return "allow"
    if command_mode == "block":
        return "block"
    # command_mode == "redact" overrides allow but not block
    if base == "block":
        return "block"
    return "redact"


def file_level(path: Path, thresholds: dict[PrivacyLevel, int] | None = None) -> PrivacyLevel:
    """Return the privacy level for a single file, using existing frontmatter when available."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    fields = read_fields(text)
    existing = fields.get("privacy_level")
    if existing in LEVELS:
        return existing  # type: ignore[return-value]
    return score_text(text, thresholds).level


# ---------------------------------------------------------------------------
# Layer 5: Optional LLM verification protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Verifier(Protocol):
    """Protocol for optional LLM-based gray-zone verification.

    Implementations receive a file excerpt and the heuristic score, and may
    return an adjusted PrivacyLevel or None to keep the heuristic result.
    The scanner itself has zero LLM dependency; callers inject an implementation.
    """

    def verify(
        self,
        path: str,
        excerpt: str,
        score: int,
        categories: dict[str, int],
    ) -> PrivacyLevel | None:
        """Return adjusted level or None to keep heuristic result."""
        ...
