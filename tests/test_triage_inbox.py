"""Inbox routing: the second triage stage (deeporbit triage --inbox).

Every test builds a fresh initialized vault in a temp dir and asserts the
deterministic routing contract: destination actions carry a `target` path,
trash/review never do, and nothing is ever moved or deleted.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from deeporbit.cli import main
from deeporbit.config import load_config
from deeporbit.triage import route_inbox, route_inbox_item, triage
from deeporbit.vault import initialize

LONG_PROSE = "这是一段足够长的正文，用来超过超短笔记的阈值。" * 3


class InboxRoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        initialize(self.root)
        self.config = load_config(self.root)
        self.inbox = self.config.path("inbox")

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, name: str, content: str = LONG_PROSE, mtime: float | None = None) -> Path:
        path = self.inbox / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if mtime is not None:
            os.utime(path, (mtime, mtime))
        return path

    def _route(self, name: str) -> dict:
        return route_inbox_item(self.config, self.inbox / name)

    # --- trash signals -------------------------------------------------

    def test_empty_note_is_trash(self):
        self._write("空白.md", "")
        result = self._route("空白.md")
        self.assertEqual(result["action"], "trash")
        self.assertIn("空", result["reason"])

    def test_whitespace_only_note_is_trash(self):
        self._write("空白.md", "  \n\n\t\n")
        self.assertEqual(self._route("空白.md")["action"], "trash")

    def test_junk_extension_is_trash(self):
        self._write("debug.log")
        self.assertEqual(self._route("debug.log")["action"], "trash")

    def test_empty_dir_is_trash(self):
        (self.inbox / "空目录").mkdir()
        self.assertEqual(self._route("空目录")["action"], "trash")

    # --- duplicate detection -------------------------------------------

    def test_exact_duplicates_trash_all_but_oldest(self):
        body = "# 同一篇笔记\n完全一样的内容。\n"
        oldest = self._write("副本A.md", body, mtime=1000)
        self._write("副本B.md", body, mtime=2000)
        self._write("副本C.md", body, mtime=3000)
        results = {item["path"]: item for item in route_inbox(self.config)}
        survivor = results[f"00_Inbox/{oldest.name}"]
        self.assertNotEqual(survivor["action"], "trash")
        for name in ("副本B.md", "副本C.md"):
            dup = results[f"00_Inbox/{name}"]
            self.assertEqual(dup["action"], "trash")
            self.assertIn(oldest.name, dup["reason"])
            self.assertIn("重复", dup["reason"])

    def test_whitespace_variants_count_as_duplicates(self):
        self._write("原始.md", "一些 内容\n\n换行\n", mtime=1000)
        self._write("变体.md", "一些  内容   换行", mtime=2000)
        results = {item["path"]: item for item in route_inbox(self.config)}
        self.assertEqual(results["00_Inbox/变体.md"]["action"], "trash")

    def test_different_content_is_not_a_duplicate(self):
        self._write("甲.md", "甲的内容，完全不一样。", mtime=1000)
        self._write("乙.md", "乙的内容，另一样东西。", mtime=2000)
        results = {item["path"]: item for item in route_inbox(self.config)}
        self.assertNotEqual(results["00_Inbox/甲.md"]["action"], "trash")
        self.assertNotEqual(results["00_Inbox/乙.md"]["action"], "trash")

    def test_duplicate_detection_is_stable_across_runs(self):
        body = "稳定吗？" * 20
        self._write("x.md", body, mtime=1000)
        self._write("y.md", body, mtime=2000)
        first = {item["path"]: item["action"] for item in route_inbox(self.config)}
        second = {item["path"]: item["action"] for item in route_inbox(self.config)}
        self.assertEqual(first, second)

    # --- frontmatter-driven routing --------------------------------------

    def test_status_note_goes_to_projects(self):
        self._write("工作项.md", "---\nstatus: active\n---\n# 项目\n" + LONG_PROSE)
        result = self._route("工作项.md")
        self.assertEqual(result["action"], "projects")
        self.assertEqual(result["target"], self.config.dir("projects"))

    def test_status_note_with_research_type_goes_to_research(self):
        self._write("调研.md", "---\nstatus: active\ntype: research\n---\n" + LONG_PROSE)
        result = self._route("调研.md")
        self.assertEqual(result["action"], "research")
        self.assertEqual(result["target"], self.config.dir("research"))

    def test_diary_type_goes_to_diary(self):
        self._write("随记.md", "---\ntype: daily\n---\n" + LONG_PROSE)
        result = self._route("随记.md")
        self.assertEqual(result["action"], "diary")
        self.assertEqual(result["target"], self.config.dir("diary"))

    def test_source_frontmatter_goes_to_notes(self):
        self._write("剪藏.md", "---\nsource: https://example.com/a\n---\n" + LONG_PROSE)
        self.assertEqual(self._route("剪藏.md")["action"], "notes")

    def test_book_id_goes_to_notes(self):
        self._write("读书.md", "---\nbook_id: wxyz\n---\n" + LONG_PROSE)
        self.assertEqual(self._route("读书.md")["action"], "notes")

    def test_external_type_goes_to_notes(self):
        self._write("论文.md", "---\ntype: paper\n---\n" + LONG_PROSE)
        self.assertEqual(self._route("论文.md")["action"], "notes")

    # --- name- and content-driven routing ---------------------------------

    def test_dated_meeting_name_goes_to_diary(self):
        self._write("会议 2026-07-08.md")
        result = self._route("会议 2026-07-08.md")
        self.assertEqual(result["action"], "diary")
        self.assertEqual(result["target"], self.config.dir("diary"))

    def test_dated_name_without_meeting_keyword_is_not_diary(self):
        self._write("计划 2026-07-08.md")
        self.assertNotEqual(self._route("计划 2026-07-08.md")["action"], "diary")

    def test_link_collection_goes_to_resources(self):
        body = "\n".join(f"- https://example.com/{i} 一些说明" for i in range(6))
        self._write("链接汇总.md", f"# 汇总\n{body}\n")
        result = self._route("链接汇总.md")
        self.assertEqual(result["action"], "resources")
        self.assertEqual(result["target"], self.config.dir("resources"))

    def test_prose_with_a_few_links_is_not_a_collection(self):
        body = LONG_PROSE + "\n参考 https://example.com/1 和 https://example.com/2。\n" + LONG_PROSE
        self._write("随笔.md", body)
        self.assertNotEqual(self._route("随笔.md")["action"], "resources")

    def test_media_file_goes_to_resources(self):
        self._write("截图.png")
        result = self._route("截图.png")
        self.assertEqual(result["action"], "resources")
        self.assertEqual(result["target"], self.config.dir("resources"))

    def test_media_dir_goes_to_resources_with_target(self):
        media = self.inbox / "附件"
        media.mkdir()
        (media / "a.pdf").write_text("x", encoding="utf-8")
        result = self._route("附件")
        self.assertEqual(result["action"], "resources")
        self.assertEqual(result["target"], self.config.dir("resources"))

    # --- safety and escalation --------------------------------------------

    def test_code_file_goes_out_of_vault(self):
        self._write("script.py")
        self.assertEqual(self._route("script.py")["action"], "out-of-vault")

    def test_secret_file_goes_out_of_vault(self):
        self._write(".env.production", "API_KEY=abc123\n")
        result = self._route(".env.production")
        self.assertEqual(result["action"], "out-of-vault")

    def test_managed_todos_file_is_kept(self):
        self._write("Todos.md", "# Todos\n- [ ] something\n")
        result = self._route("Todos.md")
        self.assertEqual(result["action"], "keep")

    def test_base64_dump_needs_review(self):
        blob = "iVBORw0KGgoAAAANSUhEUg" * 100
        self._write("粘贴.md", f"![](data:image/png;base64,{blob})\n")
        result = self._route("粘贴.md")
        self.assertEqual(result["action"], "review")
        self.assertIn("base64", result["reason"])

    def test_line_wrapped_base64_dump_needs_review(self):
        blob = "\n".join(["iVBORw0KGgoAAAANSUhEUg=="] * 80)
        self._write("粘贴.md", f"![](data:image/png;base64,\n{blob})\n")
        result = self._route("粘贴.md")
        self.assertEqual(result["action"], "review")
        self.assertIn("base64", result["reason"])

    def test_link_roundup_name_with_urls_goes_to_resources(self):
        body = "这是一份汇总，每条都有说明。\n" + "\n".join(
            f"- https://example.com/{i} —— 这条是讲第 {i} 个主题的详细介绍。" for i in range(4)
        )
        self._write("暑假链接汇总.md", body)
        result = self._route("暑假链接汇总.md")
        self.assertEqual(result["action"], "resources")
        self.assertEqual(result["target"], self.config.dir("resources"))

    def test_tiny_note_needs_review(self):
        self._write("碎片.md", "call 龙虾\n")
        result = self._route("碎片.md")
        self.assertEqual(result["action"], "review")
        self.assertIn("过短", result["reason"])

    def test_plain_prose_needs_review(self):
        self._write("想法.md", LONG_PROSE)
        self.assertEqual(self._route("想法.md")["action"], "review")

    def test_unknown_extension_needs_review(self):
        self._write("数据.xyzw")
        self.assertEqual(self._route("数据.xyzw")["action"], "review")

    def test_destinations_carry_target_but_review_and_trash_do_not(self):
        self._write("链接.md", "\n".join(f"https://e.com/{i}" for i in range(5)) + "\n补充说明\n")
        self._write("空白.md", "")
        self._write("想法.md", LONG_PROSE)
        results = {item["path"]: item for item in route_inbox(self.config)}
        self.assertIn("target", results["00_Inbox/链接.md"])
        self.assertNotIn("target", results["00_Inbox/空白.md"])
        self.assertNotIn("target", results["00_Inbox/想法.md"])

    def test_target_respects_custom_directory_mapping(self):
        self.config.directories["resources"] = "50_CustomResources"
        self._write("截图.png")
        self.assertEqual(self._route("截图.png")["target"], "50_CustomResources")

    # --- route_inbox scanning ----------------------------------------------

    def test_route_inbox_skips_dotfiles(self):
        self._write(".hidden.md")
        paths = [item["path"] for item in route_inbox(self.config)]
        self.assertNotIn("00_Inbox/.hidden.md", paths)

    def test_route_inbox_missing_dir_returns_empty(self):
        for entry in self.inbox.iterdir():
            entry.unlink()
        self.inbox.rmdir()
        self.assertEqual(route_inbox(self.config), [])

    def test_triage_inbox_flag_routes_inbox(self):
        self._write("空白.md", "")
        actions = {item["path"]: item["action"] for item in triage(self.config, inbox=True)}
        self.assertEqual(actions["00_Inbox/空白.md"], "trash")

    # --- CLI end to end ------------------------------------------------------

    def test_cli_triage_inbox_outputs_json(self):
        self._write("想法.md", LONG_PROSE)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--vault", str(self.root), "triage", "--inbox"])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertIsInstance(payload, list)
        by_path = {item["path"]: item for item in payload}
        self.assertEqual(by_path["00_Inbox/想法.md"]["action"], "review")


class InboxApplyTests(unittest.TestCase):
    """--apply executes the safe subset and never touches the rest."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        initialize(self.root)
        self.config = load_config(self.root)
        self.inbox = self.config.path("inbox")

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, name: str, content: str = LONG_PROSE, mtime: float | None = None) -> Path:
        path = self.inbox / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if mtime is not None:
            os.utime(path, (mtime, mtime))
        return path

    def _apply(self) -> dict[str, dict]:
        from deeporbit.triage import apply_routes

        results = apply_routes(self.config, route_inbox(self.config))
        return {item["path"]: item for item in results}

    def test_apply_moves_routed_file_to_target(self):
        self._write("截图.png")
        results = self._apply()
        item = results["00_Inbox/截图.png"]
        self.assertTrue(item["executed"])
        self.assertEqual(item["to"], "50_Resources/截图.png")
        self.assertTrue((self.root / "50_Resources/截图.png").exists())
        self.assertFalse((self.inbox / "截图.png").exists())

    def test_apply_trashes_empty_note_reversibly(self):
        self._write("空白.md", "")
        results = self._apply()
        item = results["00_Inbox/空白.md"]
        self.assertTrue(item["executed"])
        self.assertFalse((self.inbox / "空白.md").exists())
        self.assertTrue((self.root / ".trash" / "00_Inbox/空白.md").exists())

    def test_apply_trashes_duplicates_but_keeps_survivor(self):
        body = "一样的内容。" * 10
        self._write("a.md", body, mtime=1000)
        self._write("b.md", body, mtime=2000)
        results = self._apply()
        self.assertFalse(results["00_Inbox/a.md"]["executed"])  # survivor: review, skipped
        self.assertTrue(results["00_Inbox/b.md"]["executed"])
        self.assertTrue((self.inbox / "a.md").exists())
        self.assertFalse((self.inbox / "b.md").exists())

    def test_apply_never_touches_review_items(self):
        self._write("想法.md", LONG_PROSE)
        results = self._apply()
        item = results["00_Inbox/想法.md"]
        self.assertFalse(item["executed"])
        self.assertEqual(item["skipped"], "needs-agent")
        self.assertTrue((self.inbox / "想法.md").exists())

    def test_apply_never_touches_out_of_vault(self):
        self._write("script.py")
        results = self._apply()
        item = results["00_Inbox/script.py"]
        self.assertFalse(item["executed"])
        self.assertEqual(item["skipped"], "unsafe")
        self.assertTrue((self.inbox / "script.py").exists())

    def test_apply_keeps_managed_todos(self):
        self._write("Todos.md", "# Todos\n- [ ] x\n")
        results = self._apply()
        self.assertEqual(results["00_Inbox/Todos.md"]["skipped"], "no-op")
        self.assertTrue((self.inbox / "Todos.md").exists())

    def test_apply_never_overwrites_on_conflict(self):
        self._write("截图.png")
        existing = self.root / "50_Resources" / "截图.png"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("original", encoding="utf-8")
        results = self._apply()
        item = results["00_Inbox/截图.png"]
        self.assertFalse(item["executed"])
        self.assertIn("conflict", item["skipped"])
        self.assertEqual(existing.read_text(encoding="utf-8"), "original")
        self.assertTrue((self.inbox / "截图.png").exists())

    def test_apply_is_idempotent(self):
        self._write("空白.md", "")
        self._write("截图.png")
        first = self._apply()
        self.assertTrue(any(i["executed"] for i in first.values()))
        second = self._apply()
        self.assertFalse(any(i["executed"] for i in second.values()))

    def test_apply_creates_missing_target_dir(self):
        import shutil

        shutil.rmtree(self.root / "50_Resources")
        self._write("截图.png")
        results = self._apply()
        self.assertTrue(results["00_Inbox/截图.png"]["executed"])
        self.assertTrue((self.root / "50_Resources/截图.png").exists())

    def test_cli_triage_inbox_apply(self):
        self._write("空白.md", "")
        self._write("想法.md", LONG_PROSE)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--vault", str(self.root), "triage", "--inbox", "--apply"])
        self.assertEqual(code, 0)
        payload = {item["path"]: item for item in json.loads(buffer.getvalue())}
        self.assertTrue(payload["00_Inbox/空白.md"]["executed"])
        self.assertFalse(payload["00_Inbox/想法.md"]["executed"])
        self.assertFalse((self.inbox / "空白.md").exists())
        self.assertTrue((self.inbox / "想法.md").exists())


if __name__ == "__main__":
    unittest.main()
