import os
import json
import shutil
import sys

def get_plugin_root():
    # The script is in `<plugin_root>/scripts/`
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)

def set_language(target_lang, target_dir):
    plugin_root = get_plugin_root()
    print(f"Switching DeepOrbit language to: {target_lang} in {target_dir}")
    
    # Define source file based on requested language
    if target_lang.lower() == "zh-cn":
        source_json = os.path.join(plugin_root, "deeporbit.zh-CN.json")
    elif target_lang.lower() == "en":
        source_json = os.path.join(plugin_root, "deeporbit.en.json")
    else:
        print(f"Error: Unknown language '{target_lang}'. Available options: zh-cn, en")
        sys.exit(1)

    target_json = os.path.join(target_dir, "deeporbit.json")
    
    # Load old config to rename folders if it exists
    old_config = None
    if os.path.exists(target_json):
        try:
            with open(target_json, "r", encoding="utf-8") as f:
                old_config = json.load(f)
        except Exception as e:
            print(f"Warning: Could not read existing config at {target_json}: {e}")

    new_config = None
    # If the user asks for English but we only have deeporbit.json and deeporbit.zh-CN.json in the plugin root
    if target_lang.lower() == "en" and not os.path.exists(source_json):
        # We need to recreate the deeporbit.en.json or notify that English is default
        print("Note: Writing default English configuration directly.")
        new_config = {
          "language": "en",
          "folder_mapping": {
            "inbox": "00_Inbox",
            "diary": "10_Diary",
            "projects": "20_Projects",
            "research": "30_Research",
            "wiki": "40_Wiki",
            "resources": "50_Resources",
            "notes": "60_Notes",
            "plans": "90_Plans",
            "system": "99_System"
          }
        }
    else:
        if not os.path.exists(source_json):
            print(f"Error: Backup configuration {source_json} does not exist in the plugin directory.")
            sys.exit(1)
        with open(source_json, "r", encoding="utf-8") as f:
            new_config = json.load(f)
            
    # Rename folders before saving the new config
    if old_config and "folder_mapping" in old_config and "folder_mapping" in new_config:
        print("Checking for folders to rename...")
        for key, old_folder in old_config["folder_mapping"].items():
            new_folder = new_config["folder_mapping"].get(key)
            if new_folder and old_folder != new_folder:
                old_path = os.path.join(target_dir, old_folder)
                new_path = os.path.join(target_dir, new_folder)
                if os.path.exists(old_path):
                    if not os.path.exists(new_path):
                        try:
                            os.rename(old_path, new_path)
                            print(f"  Renamed: '{old_folder}' -> '{new_folder}'")
                        except Exception as e:
                            print(f"  Error renaming '{old_folder}': {e}")
                    else:
                        print(f"  Cannot rename '{old_folder}' to '{new_folder}' because '{new_folder}' already exists.")

    # Write new config
    with open(target_json, "w", encoding="utf-8") as f:
        json.dump(new_config, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nSuccessfully configured language for vault at {target_json}.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python switch_language.py <zh-cn|en> [target_directory]")
        sys.exit(1)
    
    lang = sys.argv[1]
    
    # Target directory defaults to current working directory
    target = os.getcwd()
    if len(sys.argv) > 2:
        target = sys.argv[2]
        
    set_language(lang, target)
