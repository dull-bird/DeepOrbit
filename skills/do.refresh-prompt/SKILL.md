---
name: do.refresh-prompt
description: |
  Safely update DeepOrbitPrompt.md in the user's vault when the DeepOrbit repo has a new version. Detects user customizations via diff and offers merge options instead of blindly overwriting.
  Triggers: "refresh prompt", "update prompt", "sync prompt", "upgrade deeporbit"
---

# Refresh System Prompt

Safely update the `DeepOrbitPrompt.md` in the user's Obsidian vault to match the latest version from the DeepOrbit repo, while preserving any user customizations.

## 🚫 CRITICAL ANTI-PATTERN
- **DO NOT** blindly overwrite the user's `DeepOrbitPrompt.md`. The user may have added custom rules, modified skills, or changed settings. Always diff first.

---

## Workflow

### Step 1: Locate Files

1. **Source (latest version):** Find the `DeepOrbitPrompt.md` from the DeepOrbit repo/extension.
   - Typical paths:
     - Extension: `~/.gemini/extensions/deeporbit/DeepOrbitPrompt.md`
     - Local clone: `<repo>/DeepOrbitPrompt.md`
   - If neither exists, ask the user for the repo path.

2. **Target (user's copy):** Find the `DeepOrbitPrompt.md` in the current vault root.
   - If it doesn't exist, this is a fresh install → just copy the source and stop.

### Step 2: Diff Comparison

Run a diff between the two files:

```bash
# On any platform with git available:
git diff --no-index --word-diff "<vault>/DeepOrbitPrompt.md" "<source>/DeepOrbitPrompt.md"
```

Or if git is not available, use Python:
```bash
python -c "
import difflib, sys
a = open(sys.argv[1]).readlines()
b = open(sys.argv[2]).readlines()
diff = difflib.unified_diff(a, b, fromfile='vault (yours)', tofile='repo (latest)', lineterm='')
print('\n'.join(diff))
" "<vault>/DeepOrbitPrompt.md" "<source>/DeepOrbitPrompt.md"
```

### Step 3: Analyze the Diff

Classify every change into one of three categories:

| Category | Description | Example |
|----------|-------------|---------|
| **Repo-only change** | New content in repo that user's copy doesn't have | New skill added, rule updated |
| **User-only change** | Content in user's copy that repo doesn't have | User added custom rules, modified settings |
| **Conflict** | Both sides changed the same section differently | Repo updated a rule that user also modified |

### Step 4: Present Options to User

Based on the diff analysis, present a clear summary and options:

```markdown
## 🔄 DeepOrbitPrompt.md Refresh Report

### Changes from Repo (new in latest version):
- [+] Added `/do:[[new-skill]]` to Core Workflows
- [+] Updated Visualization rule
- [~] Modified skill count from 21 → 23

### Your Customizations (will be preserved):
- [*] Custom rule: "Always respond in formal tone"
- [*] Added personal workflow `/do:[[my-custom]]`

### Conflicts (need your decision):
- [!] Rule "Cognitive Framework" — both you and repo modified this

---

**Choose an option:**

1. **🔄 Smart Merge (Recommended)**: Apply all repo changes while keeping your customizations. Conflicts will be resolved by keeping your version with repo additions appended.

2. **📋 Cherry-Pick**: Show me each change and I'll decide one by one.

3. **⬆️ Full Overwrite**: Replace with the latest repo version entirely. ⚠️ Your customizations will be lost.

4. **❌ Cancel**: Keep my current version, don't change anything.
```

### Step 5: Execute the Chosen Option

#### Option 1: Smart Merge
1. Start with the user's current file as base.
2. Apply repo-only additions (new skills, new rules) into the appropriate sections.
3. Keep user-only additions unchanged.
4. For conflicts: keep the user's version, but add a comment marking the repo's version:
   ```markdown
   <!-- REPO UPDATE (review and remove this comment):
   Original repo version of this rule:
   - ...
   -->
   ```

#### Option 2: Cherry-Pick
For each change, show the diff and ask: "Apply this? (y/n/edit)"

#### Option 3: Full Overwrite
Copy the repo version to the vault. Backup the old file as `DeepOrbitPrompt.md.backup`.

#### Option 4: Cancel
Do nothing.

### Step 6: Post-Refresh

1. Remind the user to run `/memory refresh` in Gemini CLI to reload the prompt.
2. If `deeporbit.json` also has changes, offer to update it similarly.
3. Report what was changed:

```markdown
## ✅ Refresh Complete

- Applied: 5 repo changes
- Preserved: 2 user customizations
- Conflicts resolved: 1 (your version kept, repo version in comment)
- Backup: `DeepOrbitPrompt.md.backup`

Run `/memory refresh` to reload.
```

## Rules

- Read `deeporbit.json` from the workspace root to determine the interaction language. Use this language for all your responses and generated note contents (e.g. `zh-CN`). **The Obsidian folder paths themselves will ALWAYS remain in English.**
