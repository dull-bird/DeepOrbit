import os
import glob
import re

folder_map = {
    "00_收件箱": "[inbox_folder]",
    "10_日记": "[diary_folder]",
    "20_项目": "[projects_folder]",
    "30_研究": "[research_folder]",
    "40_知识库": "[wiki_folder]",
    "50_资源": "[resources_folder]",
    "60_笔记": "[notes_folder]",
    "90_计划": "[plans_folder]",
    "99_系统": "[system_folder]"
}

repo_root = r"d:\work\repos\DeepOrbit"
skills_dir = os.path.join(repo_root, "skills")

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content
    for old_val, new_val in folder_map.items():
        # Replace only if not already containing the placeholder
        new_content = new_content.replace(old_val, new_val)
    
    # Also replace Language rules if present
    language_rule = "Match the language of the user's input (or inbox file content) for all responses and generated files."
    new_language_rule = "Read `deeporbit.json` from the workspace root to determine the interaction language and exactly which folder paths to use. Use the language specified in the config for all responses and generated files. (e.g. `zh-CN` for Chinese)."
    new_content = new_content.replace(language_rule, new_language_rule)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated: {filepath}")

for root, dirs, files in os.walk(skills_dir):
    for file in files:
        if file.endswith(".md") or file.endswith(".py"):
            replace_in_file(os.path.join(root, file))

print("Replacements complete.")
