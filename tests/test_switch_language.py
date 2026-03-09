import os
import sys
import json
import shutil
import unittest
import tempfile
from pathlib import Path

# Add scripts directory to path to import the module
scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, scripts_dir)
import switch_language

class TestSwitchLanguage(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory to act as the plugin root AND the vault
        self.test_dir = tempfile.mkdtemp()
        self.plugin_root = self.test_dir
        self.vault_dir = self.test_dir

        # Mock the get_plugin_root function to return our test dir
        self.original_get_plugin_root = switch_language.get_plugin_root
        switch_language.get_plugin_root = lambda: self.plugin_root

        # Create mock deeporbit.zh-CN.json
        self.zh_config = {
            "language": "zh-CN",
            "folder_mapping": {
                "inbox": "00_收件箱",
                "diary": "10_日记"
            }
        }
        with open(os.path.join(self.plugin_root, "deeporbit.zh-CN.json"), "w", encoding="utf-8") as f:
            json.dump(self.zh_config, f, ensure_ascii=False)

        # Create mock deeporbit.en.json
        self.en_config = {
            "language": "en",
            "folder_mapping": {
                "inbox": "00_Inbox",
                "diary": "10_Diary"
            }
        }
        with open(os.path.join(self.plugin_root, "deeporbit.en.json"), "w", encoding="utf-8") as f:
            json.dump(self.en_config, f, ensure_ascii=False)

    def tearDown(self):
        # Restore original function
        switch_language.get_plugin_root = self.original_get_plugin_root
        # Clean up temp directory
        shutil.rmtree(self.test_dir)

    def test_switch_from_en_to_zh(self):
        # 1. Setup initial EN state
        # Create the EN config in vault
        with open(os.path.join(self.vault_dir, "deeporbit.json"), "w", encoding="utf-8") as f:
            json.dump(self.en_config, f, ensure_ascii=False)
        
        # Create physical EN folders
        os.makedirs(os.path.join(self.vault_dir, "00_Inbox"))
        os.makedirs(os.path.join(self.vault_dir, "10_Diary"))

        # 2. Perform switch
        switch_language.set_language("zh-cn", self.vault_dir)

        # 3. Assertions
        # Check active config
        with open(os.path.join(self.vault_dir, "deeporbit.json"), "r", encoding="utf-8") as f:
            active_config = json.load(f)
        self.assertEqual(active_config["language"], "zh-CN")

        # Check folder renaming
        self.assertFalse(os.path.exists(os.path.join(self.vault_dir, "00_Inbox")))
        self.assertFalse(os.path.exists(os.path.join(self.vault_dir, "10_Diary")))
        self.assertTrue(os.path.exists(os.path.join(self.vault_dir, "00_收件箱")))
        self.assertTrue(os.path.exists(os.path.join(self.vault_dir, "10_日记")))

    def test_switch_from_zh_to_en(self):
        # 1. Setup initial ZH state
        # Create the ZH config in vault
        with open(os.path.join(self.vault_dir, "deeporbit.json"), "w", encoding="utf-8") as f:
            json.dump(self.zh_config, f, ensure_ascii=False)
        
        # Create physical ZH folders
        os.makedirs(os.path.join(self.vault_dir, "00_收件箱"))
        
        # 2. Perform switch
        switch_language.set_language("en", self.vault_dir)

        # 3. Assertions
        # Check active config
        with open(os.path.join(self.vault_dir, "deeporbit.json"), "r", encoding="utf-8") as f:
            active_config = json.load(f)
        self.assertEqual(active_config["language"], "en")

        # Check folder renaming (00_收件箱 should be renamed)
        self.assertFalse(os.path.exists(os.path.join(self.vault_dir, "00_收件箱")))
        self.assertTrue(os.path.exists(os.path.join(self.vault_dir, "00_Inbox")))
        
        # 10_日记 was never created, so it shouldn't be renamed, but the process shouldn't crash
        self.assertFalse(os.path.exists(os.path.join(self.vault_dir, "10_Diary")))

if __name__ == '__main__':
    unittest.main()
