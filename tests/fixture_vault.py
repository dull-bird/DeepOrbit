"""Builds a realistic, messy vault used by integration tests.

The fixture deliberately includes every situation the lifecycle and migration
code must handle: active/paused/done projects (file and folder form), a
processed inbox item, a draft writing, an active research note, a legacy
localized folder, and a note without frontmatter.
"""

from __future__ import annotations

from pathlib import Path

FILES: dict[str, str] = {
    "00_Inbox/processed-idea.md": """---
status: processed
created: 2026-07-10
---
# Idea about index tracking
Converted to [[ActiveProject]].
""",
    "00_Inbox/raw-thought.md": "Just a thought, no frontmatter yet.\n",
    "20_Projects/ActiveProject/ActiveProject.md": """---
type: project
status: active
area: "[[AI]]"
created: 2026-06-01
updated: 2026-06-10
tags: [project]
---
# Active Project

## Tasks
- [ ] Ship the milestone #task ^do-20260701090000-aaaaaa
""",
    "20_Projects/ActiveProject/assets/spec.txt": "asset payload\n",
    "20_Projects/DoneProject.md": """---
type: project
status: done
created: 2026-03-01
updated: 2026-06-15
tags: [project]
---
# Done Project
""",
    "20_Projects/PausedProject.md": """---
type: project
status: paused
created: 2026-04-01
updated: 2026-05-20
tags: [project]
---
# Paused Project
""",
    "30_Research/RAG-Survey.md": """---
type: research
status: active
area: "[[AI]]"
created: 2026-06-20
updated: 2026-06-20
---
# RAG Survey
Retrieval augmented generation survey notes about lexical baselines.
""",
    "30_Research/Agent-Digest.md": """---
type: research
status: active
author: ai
created: 2026-07-08
updated: 2026-07-08
---
# Agent Digest
AI-generated research digest.
""",
    "15_Writings/essay.md": """---
status: draft
created: 2026-07-02
---
# Essay draft
""",
    "40_Wiki/RAG.md": """---
type: wiki
created: 2026-06-01
---
# RAG
Retrieval augmented generation concept note.
""",
    "40_Wiki/ActiveConcept.md": """---
type: wiki
status: active
created: 2026-05-01
---
# Active Concept
A wiki note that should never count as lifecycle work.
""",
    "60_Notes/微信读书/测试书A.md": """---
title: "测试书A"
book_id: "23523085"
source: "微信读书"
status: 在读
---
# 测试书A
""",
    "60_Notes/微信读书/测试书B.md": """---
title: "测试书B"
book_id: "23523086"
source: "微信读书"
status: 未读
---
# 测试书B
""",
    "60_Notes/微信读书/测试书C.md": """---
title: "测试书C"
book_id: "23523087"
source: "微信读书"
status: 读完
---
# 测试书C
""",
    "50_Resources/产品发布/legacy-note.md": "legacy localized resource\n",
    "20_Projects/微信读书记录/2026-06-16-读书记录.md": "# 2026-06-16 读书记录\n\nAgent-written reading analysis, no sync frontmatter.\n",
}


def build_messy_vault(root: Path) -> Path:
    for rel, content in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root
