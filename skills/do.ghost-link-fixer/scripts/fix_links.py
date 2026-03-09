import os
import re
from datetime import datetime

# 配置
VAULT_ROOT = os.getcwd()
KB_PATH = os.path.join(VAULT_ROOT, "[wiki_folder]")
TEMPLATE_PATH = os.path.join(VAULT_ROOT, "[system_folder]", "模板", "Wiki_Template.md")

def get_all_md_files():
    md_files = []
    for root, _, files in os.walk(VAULT_ROOT):
        for file in files:
            if file.endswith(".md"):
                md_files.append(os.path.splitext(file)[0])
    return set(md_files)

def find_ghost_links():
    ghost_links = set()
    existing_files = get_all_md_files()
    link_regex = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
    
    for root, _, files in os.walk(KB_PATH):
        for file in files:
            if file.endswith(".md"):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = link_regex.findall(content)
                        for match in matches:
                            clean_link = match.strip()
                            if "/" not in clean_link and "\\" not in clean_link and len(clean_link) > 0:
                                if clean_link not in existing_files and clean_link != "AreaName":
                                    ghost_links.add(clean_link)
                except Exception:
                    pass
    return ghost_links

def create_note(name):
    target_dir = os.path.join(KB_PATH, "未分类")
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    target_path = os.path.join(target_dir, f"{name}.md")
    if os.path.exists(target_path):
        return None

    template_content = ""
    today = datetime.now().strftime("%Y-%m-%d")
    
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            template_content = f.read()
            template_content = template_content.replace("{{date:YYYY-MM-DD}}", today)
            template_content = template_content.replace("[概念名称]", name)
    
    with open(target_path, 'w', encoding='utf-8') as f:
        if template_content:
            f.write(template_content)
        else:
            f.write(f"---\ntags: [ghost-link]\ncreated: {today}\n---\n# {name}\n\n内容待填充。")
    return name

if __name__ == "__main__":
    ghosts = find_ghost_links()
    created_list = []
    if ghosts:
        for ghost in ghosts:
            if not re.search(r'[^\w\s\u4e00-\u9fff\-]', ghost):
                name = create_note(ghost)
                if name:
                    created_list.append(name)
    
    if created_list:
        print("CREATED_FILES:" + ",".join(created_list))
    else:
        print("NO_NEW_FILES")
