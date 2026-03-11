---
name: do.note-summary
description: |
  Fetch and summarize any content (URL, PDF, local file, audio/video) into a structured Markdown note with completeness verification. Supports three depth levels: Quick (skim), Standard (default), and Deep (paper-grade analysis with critical review). Automatically detects content type and adjusts workflow.
  Triggers: "note summary", "summarize", "read paper", "paper reading", "summarize this", "skim", "deep read", "精读"
---

# Note Summary Skill

Fetch, read, and summarize any content into structured Markdown notes with **guaranteed completeness**. Uses a phased workflow with depth control and a post-generation quality checklist.

## 🚫 CRITICAL ANTI-PATTERNS
- **DO NOT** summarize based on abstracts, titles, or metadata alone. You MUST obtain the full original content.
- **DO NOT** produce the entire summary in one monolithic pass for long content. Break it into sections.
- **DO NOT** invent or hallucinate information not present in the source.

---

## Depth Modes

The skill supports three depth levels, auto-detected or user-specified:

| Mode | Trigger | What You Do |
|------|---------|-------------|
| **Quick** | User says "quick", "skim", "glance" | Phase 1 only → 3-line summary |
| **Standard** | User says "standard", "brief" | Phase 1 + Phase 2 → full structured summary |
| **Deep** | **Default**. Also triggered by "deep", "critique", "精读" | Phase 1 + Phase 2 + Phase 3 → full summary + critical analysis |

If unsure, default to **Deep**.

---

## Workflow

### Phase 0: Input Detection & Content Fetching

Identify the input type and fetch the complete source content.

**Input types:**

| Type | Detection | Action |
|------|-----------|--------|
| **URL (web page)** | Starts with `http` | Fetch full page content |
| **URL (arXiv)** | Contains `arxiv.org` | Visit `/abs/` for metadata, then read the PDF via `read_file` |
| **URL (audio/video)** | YouTube, podcast, etc. | Extract subtitles via `yt-dlp` or transcription tools |
| **Local PDF** | `.pdf` extension | Use `read_file` to visually read (multimodal) |
| **Local Markdown** | `.md` extension | Read directly |
| **Paper title / topic** | No URL, looks like a title | Search for it, find the source, fetch full text |

**Error handling:**
- If only an abstract is obtainable after retries, prepend a bold warning:
  > ⚠️ **Warning: Full text not found. This summary is based solely on the abstract.**
- If audio/subtitle extraction fails after all fallback attempts, report error and stop.

---

### Phase 1: Screening (海选) — ~5-10 minutes

**Goal:** Understand what the content is about. Determine category and depth.

1. **Skim** the content: read title, introduction/abstract, conclusion, and key figures.
2. **Categorize** the content:

| Category | Examples |
|----------|---------|
| `papers` | Academic papers, research reports |
| `podcasts` | Interview transcripts, long-form audio |
| `videos` | YouTube summaries, tutorials |
| `articles` | Blogs, news, technical tutorials |

3. **Build the Section Manifest** — create a mental (or written) outline of all major sections:

```
Manifest for: <title>
- [ ] Section 1: <heading> (approx scope)
- [ ] Section 2: <heading>
- [ ] ...
- [ ] Section N: <heading>
- Tables: T
- Figures: F
```

4. **Write the preliminary output:**
   - Frontmatter (complete)
   - `> Core Summary` (1-2 sentences)
   - `## 1. Key Insights` (preliminary, 2-3 bullet points)

**Decision point:**
- If user requested **Quick** mode → finalize and stop here.
- Otherwise → proceed to Phase 2.

---

### Phase 2: Structured Summarization

**Goal:** Produce a complete, section-by-section summary.

**For each section in the manifest:**

1. **READ** the section carefully.
2. **SUMMARIZE** with:
   - Key points with source references (timestamps for audio/video, section numbers for papers)
   - Preserved technical terms and proper nouns
   - Mermaid diagram if the section contains a process flow or concept hierarchy (use `do.mermaid` skill for syntax)
3. **CHECK OFF** the section in the manifest.
4. **Link concepts** — identify core concepts and create `[[wikilinks]]` to `40_Wiki/`.

**After all sections:**
- Update `## 1. Key Insights` with refined understanding.
- Write `## 3. Socratic Questions` (≥2 challenging questions).
- Write `## 4. Related Concepts` with wikilinks.

**Decision point:**
- If **Standard** mode → proceed to Phase 4 (Quality Checklist).
- If **Deep** mode → proceed to Phase 3.

---

### Phase 3: Deep Analysis (精读) — Papers & Deep Mode Only

**Goal:** Critical analysis with mental reimplementation (Li Mu's Three-Pass Method, Pass 3).

For each major claim in the content, ask:
- What exactly is being claimed?
- What is the evidence?
- What are the hidden assumptions?
- Could this be done better?

**"Mental Reimplementation" test:**
- Can you close the paper and explain the core method from memory?
- Can you identify at least one weakness or improvement?

**Output — append `## 5. Critical Analysis`:**

```markdown
## 5. Critical Analysis

### Strengths
* ...

### Weaknesses / Limitations
* ...

### Potential Improvements
* ...

### Future Directions
* ...
```

**For papers — Citation Double-Linking:**

Discover citation relationships. If related articles exist in `60_Notes`, use precise double links:

🚨 **Format:** `[[<Paper Name>_summary|<Paper Name>]]` — never bare `[[Paper Name]]`.

```markdown
**References:**
- [[Attention Is All You Need_summary|Attention Is All You Need]]

**Cited By:**
- DepthAnything-v2 (Title only, not in vault)
```

---

### Phase 4: Quality Checklist (MANDATORY)

Before finalizing, **you MUST verify every item.** If any item fails, go back and fix it.

```markdown
## Output Quality Checklist
- [ ] Frontmatter complete (type, title, category, date, source, tags)
- [ ] Core summary present (1-2 sentences, first-principles decomposition)
- [ ] Key insights listed (≥2 points with concise explanations)
- [ ] Detailed structure covers ALL major sections from source
- [ ] Source references included (timestamps, section numbers, page numbers)
- [ ] Mermaid diagram generated for key process/concept (if applicable)
- [ ] Socratic questions posed (≥1, genuinely challenging)
- [ ] Wikilinks added for key concepts → 40_Wiki
- [ ] Source reference in frontmatter is accurate and linked
- [ ] (Papers only) Citation links use [[Name_summary|Name]] format
- [ ] (Papers only) Critical analysis section present (Deep mode)
- [ ] (Audio/Video only) Subtitle file saved as source, audio deleted
```

**Do NOT finalize the note until all applicable items are checked.**

---

### Phase 5: Archive & Link

1. **Storage path:** `60_Notes/<Category>/<Title>/`
   - Summary: `<Title>_summary.md`
   - Original file (if local): copy to same directory
   - Example: `60_Notes/papers/Attention Is All You Need/Attention Is All You Need_summary.md`

2. **For audio/video:** Save the complete subtitle file as `source`, delete audio (`.m4a` files are too large).

3. **Search vault** for the most relevant existing note to append a cross-reference link.

---

## Output Template

```markdown
---
type: note
title: "<Title>"
category: "<Category>"
date: YYYY-MM-DD
source: "[[<Original Filename or URL>]]"
depth: quick | standard | deep
tags:
  - <Tag1>
---

# <Title> Summary

> Core Summary: <1-2 sentences, first-principles decomposition of core value>

## 1. Key Insights

* <Insight 1>: Concise explanation.
* <Insight 2>: Concise explanation.

## 2. Detailed Structure / Key Discussion

### <Section A>

* <Key point + source reference>
* <Mermaid diagram if applicable>

### <Section B>

* <Key point + source reference>

## 3. Socratic Questions

* <Challenging question 1>
* <Challenging question 2>

## 4. Related Concepts

* [[Concept 1]]: Why it relates to this content.
* [[Concept 2]]: Connection explained.

## 5. Critical Analysis (Deep mode only)

### Strengths
* ...
### Weaknesses / Limitations
* ...
### Potential Improvements
* ...
### Future Directions
* ...
```

## Rules

- Read `deeporbit.json` from the workspace root to determine the interaction language. Use this language for all your responses and generated note contents (e.g. `zh-CN`). **The Obsidian folder paths themselves will ALWAYS remain in English.**
- Use `do.mermaid` skill for all diagram syntax. Do not inline Mermaid rules.
