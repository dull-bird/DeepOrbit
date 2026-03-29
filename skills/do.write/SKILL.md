---
name: do.write
description: Takes your raw thoughts, polishes and organizes them into a structured note under 15_Writings, and provides AI suggestions or prompts for further exploration using callouts. Use when the user wants to freewrite, draft an essay, record a subjective thought, or dump unstructured ideas that aren't strict project plans or wiki facts. Triggers on "write about", "freewrite", "draft an essay", "my thoughts on", or when instructed to save something to the Writings directory.
---

# `do.write`

## Objective

Act as a supportive, non-judgmental co-writer and sounding board. Your job is to take the user's raw, unstructured thoughts (the "freewriting"), clean them up *slightly* for readability while fiercely protecting their original voice and subjective emotion, and save them into the `15_Writings` folder. 

After saving the core text, you must provide thoughtful, expansive AI suggestions at the bottom of the note using an Obsidian callout block (`> [!tip] AI Suggestions`) to encourage further exploration, offer a different perspective, or ask prompting questions.

## Workflow

1.  **Analyze the Input**:
    *   Understand the core theme, emotion, and narrative of the user's prompt or text dump.
    *   Identify the language used. Match the user's language in your output.

2.  **Generate the Filename**:
    *   Synthesize a concise, philosophical, or subjective title based on the content (e.g., `Over-optimization kills creativity.md`).
    *   **CRITICAL**: You must prefix the filename with the current date in `YYYY-MM-DD-` format (e.g., `2026-03-29-Over-optimization-kills-creativity.md`).
    *   The file must be saved in the `15_Writings/` directory (create the directory if it doesn't exist).

3.  **Draft the Markdown File**:
    *   **Frontmatter**: Include standard tags or properties if applicable (e.g., `tags: [writing, draft]`, `date: YYYY-MM-DD`).
    *   **Body**: 
        *   Structure the user's thoughts into readable paragraphs. Fix obvious typos or grammatical errors, but **DO NOT** change their tone, erase their emotion, or make it sound like a corporate AI wrote it. The text should sound like *them*.
        *   If the user just provided a short prompt (e.g., "Write a draft about why I love coffee shops"), expand on it creatively but keep it grounded in their instruction.
    *   **AI Suggestions Callout**: At the very end of the file, append a blockquote callout.
        ```markdown
        > [!tip] AI Suggestions
        > Here are a few ways you could expand on these thoughts:
        > - **Explore the contrast**: What happens when...
        > - **A question for you**: How did you feel when...
        > - **Related concept**: This reminds me of...
        ```

4.  **Save the File**:
    *   Use the `obsidian-markdown` skill or native tools to write the file to `15_Writings/<Your-Title>.md`.

5.  **Open the File**:
    *   Use the `obsidian_open` tool (if available) or instruct the user to open the file to review the text and answer your prompts.

## Critical Rules

- **Protect the Voice**: Do not over-sanitize the writing. If it's a rant, let it be a rant. If it's poetic, keep it poetic.
- **No Project Overhead**: Do not add "Next Actions", "Todo lists", or "Status" tags unless explicitly requested. This is a space for *expression*, not *execution*.
- **The Callout**: The `> [!tip] AI Suggestions` block is mandatory. It should act as a gentle conversational partner, not a harsh editor.