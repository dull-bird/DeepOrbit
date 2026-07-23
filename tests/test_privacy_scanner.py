from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from deeporbit.privacy_scanner import (
    CATEGORY_CAP,
    DEFAULT_THRESHOLDS,
    PrivacyScore,
    Verifier,
    effective_mode,
    level_for_score,
    scan_file,
    score_text,
)
from deeporbit.content_signals import (
    detect_source_signals,
    detect_voice_signals,
    filename_signal,
    length_factor,
)


class PrivacyScannerTests(unittest.TestCase):
    def test_low_text(self):
        score = score_text("This is a general note about programming.")
        self.assertEqual(score.score, 0)
        self.assertEqual(score.level, "low")

    def test_medium_text_with_interview_keywords(self):
        score = score_text(
            "My interview last week was about resume, work experience, and an upcoming job offer."
        )
        self.assertGreaterEqual(score.score, DEFAULT_THRESHOLDS["medium"])
        self.assertEqual(score.level, "medium")

    def test_high_text_with_family_and_health(self):
        score = score_text(
            "My mother and family visited the hospital; she received a diagnosis and treatment."
        )
        self.assertGreaterEqual(score.score, DEFAULT_THRESHOLDS["high"])
        self.assertLess(score.score, DEFAULT_THRESHOLDS["critical"])
        self.assertEqual(score.level, "high")

    def test_critical_text_with_id_and_phone(self):
        score = score_text(
            "身份证号 110101199001011234，"
            "电话 138-1234-5678，"
            "地址 北京市朝阳区，"
            "邮箱 alice@example.com，"
            "工资 50000，"
            "sk-1234567890abcdef1234"
        )
        self.assertGreaterEqual(score.score, DEFAULT_THRESHOLDS["critical"])
        self.assertEqual(score.level, "critical")

    def test_email_and_secret_patterns(self):
        score = score_text("Contact me at alice@example.com and use sk-1234567890abcdef1234")
        self.assertGreaterEqual(score.score, 4)
        self.assertIn("email", score.patterns)
        self.assertIn("secret", score.patterns)

    def test_scan_file_reads_existing_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "note.md"
            path.write_text("---\nprivacy_level: high\n---\n\nSome text.", encoding="utf-8")
            result = scan_file(path)
            self.assertEqual(result.existing_level, "high")
            self.assertEqual(result.level, "low")

    def test_effective_mode_command_allow_overrides_block(self):
        self.assertEqual(effective_mode("critical", "allow"), "allow")

    def test_effective_mode_command_block_overrides_allow(self):
        self.assertEqual(effective_mode("low", "block"), "block")

    def test_effective_mode_default_enforcement(self):
        self.assertEqual(effective_mode("critical", None), "block")
        self.assertEqual(effective_mode("high", None), "redact")
        self.assertEqual(effective_mode("medium", None), "allow")
        self.assertEqual(effective_mode("low", None), "allow")

    def test_custom_thresholds(self):
        thresholds = {"low": 0, "medium": 5, "high": 10, "critical": 20}
        self.assertEqual(level_for_score(4, thresholds), "low")
        self.assertEqual(level_for_score(5, thresholds), "medium")
        self.assertEqual(level_for_score(10, thresholds), "high")
        self.assertEqual(level_for_score(20, thresholds), "critical")


class CategoryCapTests(unittest.TestCase):
    """Layer 1: category cap prevents single-topic domination."""

    def test_mental_keywords_capped(self):
        # 20 repetitions of mental keywords should be capped
        text = "焦虑 " * 20  # each match weight=1, raw=20 but capped to 6
        score = score_text(text)
        self.assertLessEqual(score.categories.get("mental", 0), CATEGORY_CAP)
        self.assertLessEqual(score.score, CATEGORY_CAP)

    def test_family_keywords_capped(self):
        text = "母亲 父亲 家庭 妻子 丈夫 孩子 儿子 女儿 " * 5
        score = score_text(text)
        self.assertLessEqual(score.categories.get("family", 0), CATEGORY_CAP)

    def test_multiple_categories_each_capped_independently(self):
        text = "焦虑 抑郁 心理 " * 10 + "母亲 父亲 家庭 " * 10
        score = score_text(text)
        self.assertLessEqual(score.categories.get("mental", 0), CATEGORY_CAP)
        self.assertLessEqual(score.categories.get("family", 0), CATEGORY_CAP)


class ContentSignalsTests(unittest.TestCase):
    """Layers 2-4: length, source, and voice signals."""

    def test_length_factor_short_doc(self):
        self.assertEqual(length_factor(200), 1.0)

    def test_length_factor_long_doc(self):
        self.assertLess(length_factor(10000), 0.5)

    def test_source_detection_urls(self):
        text = "See https://a.com and https://b.com and https://c.com for details."
        factor = detect_source_signals(text, {})
        self.assertLessEqual(factor, 0.5)

    def test_source_detection_frontmatter_source(self):
        factor = detect_source_signals("Some text", {"source": "[[paper.pdf]]"})
        self.assertLessEqual(factor, 0.3)

    def test_source_detection_transcript_format(self):
        text = "00:00 **Joe:** Hello\n00:05 **Jim:** Hi\n00:10 **Joe:** Yes\n00:15 **Jim:** No\n00:20 **Joe:** OK\n00:25 **Jim:** Bye"
        factor = detect_source_signals(text, {})
        self.assertLessEqual(factor, 0.4)

    def test_source_detection_table_data(self):
        rows = "| col1 | col2 |\n" * 15
        factor = detect_source_signals(rows, {})
        self.assertLessEqual(factor, 0.5)

    def test_source_no_signals_returns_one(self):
        factor = detect_source_signals("Just a plain personal note.", {})
        self.assertEqual(factor, 1.0)

    def test_voice_detection_first_person_emotion(self):
        text = "我很焦虑。我很害怕。我感到无助。"
        factor = detect_voice_signals(text, {})
        self.assertGreaterEqual(factor, 1.3)

    def test_voice_detection_named_person_action(self):
        text = "母亲今天去医院检查了。"
        factor = detect_voice_signals(text, {})
        self.assertGreaterEqual(factor, 1.2)

    def test_voice_no_signals_returns_one(self):
        factor = detect_voice_signals("This is an academic paper about AI.", {})
        self.assertEqual(factor, 1.0)

    def test_filename_signal_sensitive(self):
        self.assertEqual(filename_signal("简历.md"), 3)
        self.assertEqual(filename_signal("病历.md"), 3)

    def test_filename_signal_neutral(self):
        self.assertEqual(filename_signal("Attention Is All You Need.md"), 0)

    def test_filename_signal_capped(self):
        # Multiple sensitive keywords still capped at 3
        self.assertLessEqual(filename_signal("简历-面试-密码.md"), 3)


class ScanFileV2PipelineTests(unittest.TestCase):
    """Integration tests for the full 5-layer pipeline via scan_file."""

    def test_public_paper_with_emails_downgraded(self):
        """A paper with author emails should NOT be critical."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "paper.md"
            path.write_text(
                "---\nsource: '[[paper.pdf]]'\ntype: paper\n---\n\n"
                "# Attention\n\nAuthor: avaswani@google.com, noam@google.com\n"
                "Contact: illia@google.com, jacob@google.com\n",
                encoding="utf-8",
            )
            result = scan_file(path)
            self.assertIn(result.level, ("low", "medium"))

    def test_podcast_transcript_downgraded(self):
        """A podcast transcript discussing family/health should be low."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transcript.md"
            lines = []
            for i in range(20):
                lines.append(f"{i:02d}:00 **Joe:** My mother and family visited the hospital.")
                lines.append(f"{i:02d}:30 **Jim:** Yes, my father had a diagnosis and treatment.")
            path.write_text("\n".join(lines), encoding="utf-8")
            result = scan_file(path)
            self.assertIn(result.level, ("low", "medium"))

    def test_short_personal_diary_upgraded(self):
        """A short first-person medical diary should be high/critical."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "日记.md"
            path.write_text(
                "---\ntype: diary\ndate: 2026-02-12\n---\n\n"
                "2月12日 今天带母亲去医院做生化检查。\n"
                "我很担心她的肿瘤标志物偏高。\n"
                "医生说需要进一步诊断，我很焦虑。\n"
                "母亲今天状态不好，我感到无助。\n",
                encoding="utf-8",
            )
            result = scan_file(path)
            self.assertIn(result.level, ("high", "critical"))

    def test_long_research_with_urls_downgraded(self):
        """A long research doc with many URLs and keywords should be low."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "research.md"
            body = "## 调研\n\n"
            for i in range(50):
                body += f"- 心理健康工具 https://example.com/tool{i} 焦虑 抑郁\n"
            path.write_text(body, encoding="utf-8")
            result = scan_file(path)
            self.assertIn(result.level, ("low", "medium"))

    def test_explain_fields_populated(self):
        """scan_file should populate debugging fields."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "note.md"
            path.write_text("Simple note.", encoding="utf-8")
            result = scan_file(path)
            self.assertEqual(result.source_factor, 1.0)
            self.assertEqual(result.voice_factor, 1.0)
            self.assertEqual(result.length_factor, 1.0)
            self.assertEqual(result.filename_signal, 0)


class VerifierProtocolTests(unittest.TestCase):
    """Layer 5: optional LLM verifier integration."""

    def test_verifier_protocol_is_runtime_checkable(self):
        class MockVerifier:
            def verify(self, path, excerpt, score, categories):
                return "low"

        self.assertIsInstance(MockVerifier(), Verifier)

    def test_verifier_can_override_gray_zone(self):
        class DowngradeVerifier:
            def verify(self, path, excerpt, score, categories):
                return "low"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gray.md"
            # Craft text that scores in gray zone (6-14)
            path.write_text(
                "面试 工作经历 offer 入职 离职 跳槽 背调 推荐信",
                encoding="utf-8",
            )
            result_no_v = scan_file(path)
            result_v = scan_file(path, verifier=DowngradeVerifier())
            # If score is in gray zone, verifier should override
            if DEFAULT_THRESHOLDS["high"] - 2 <= result_no_v.score <= DEFAULT_THRESHOLDS["critical"] + 2:
                self.assertEqual(result_v.level, "low")

    def test_verifier_not_called_outside_gray_zone(self):
        calls = []

        class TrackingVerifier:
            def verify(self, path, excerpt, score, categories):
                calls.append(score)
                return None

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "safe.md"
            path.write_text("Just a normal note about programming.", encoding="utf-8")
            scan_file(path, verifier=TrackingVerifier())
            self.assertEqual(len(calls), 0)  # score=0, not in gray zone


if __name__ == "__main__":
    unittest.main()
