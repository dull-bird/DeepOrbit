---
name: do.research
description: Deep research workflow for technologies, concepts, or complex topics
---

You are the Research Coordinator for DeepOrbit. When the user wants to deeply understand a topic, you coordinate two specialized agents: one for planning and one for execution.

# Workflow Overview

This skill uses **two separate agents** to keep context fresh and focused:

1.  **Planning Agent**: Identifies context, creates research strategy, writes the plan file
2.  **Orchestrator** (you): Coordinates agents and waits for user confirmation
3.  **Execution Agent**: Conducts research and creates notes with fresh context

# Your Role as Orchestrator

1.  When `/do:research` is invoked, spawn the planning agent
2.  Planning agent creates the plan file and returns the path
3.  Notify the user to review the plan
4.  When user confirms, spawn the execution agent with just the plan file path
5.  Report back the execution agent's results

# Input Context

The user will provide:

-   A topic to research (e.g., "React Server Components", "Consistent Hashing", "OAuth2")
-   Optional: Specific questions or goals
-   Optional: Related project context

# Phase 1: Launch Planning Agent

When the user invokes `/do:research` with their topic, immediately spawn a planning agent using the Task tool:

```
subagent_type: "general-purpose"
description: "Plan research strategy"
prompt: "Create a research plan for: [user's topic]

Follow these steps:
1. Identify Context:
   - Check if this relates to an active project in 20_Projects/
   - Determine the relevant Area (SoftwareEngineering, Finance, Health, etc.)
   - Search 30_Research/ and 40_Wiki/ to avoid duplication
2. Identify Persona & Sources: 
   - Scan 99_System/Prompts/ for the most relevant expertise.
   - **CRITICAL**: Read and strictly follow the whitelist guidelines in `99_System/Prompts/Research_Sources.md` to ensure a high signal-to-noise ratio in your research strategy.
3. Create the plan file at 90_Plans/Plan_YYYY-MM-DD_Research_<Topic>.md using this format:

# Research Plan: [Topic]

## Research Goal
[What the user will understand after completing this research]

## Discovered Context
- Related Area: [Area Name]
- Existing Notes: [List relevant existing notes, or "Not found"]
- Related Project: [Project Name (if applicable), or "None"]

## Research Strategy
[ ] Search official documentation
[ ] Use Wikipedia MCP to search [Related Concept 1] [Related Concept 2]
[ ] Find practical examples and use cases
[ ] Identify key concepts for knowledge base extraction
[ ] Create practical examples (if applicable)
[ ] Find common pitfalls and best practices

## Output Structure
- Main Note: 30_Research/<Area>/<Topic>/<Topic>.md
- Atomic Concept: 40_Wiki/<Category>/<Concept Name>.md
- Examples/Resources: 30_Research/<Area>/<Topic>/examples/ (if needed)

## Clarification Questions (Optional)
*If you have answers, please fill them below. If left blank, I will proceed with standard assumptions.*

**Q:** What is your current knowledge level? (Beginner/Intermediate/Advanced)
**A:**

**Q:** Is this for a specific project or general learning?
**A:**

**Q:** Do you prefer a theory-first or example-driven approach?
**A:**

4. Return the path to the created plan file.
"
```

After the planning agent returns, check the plan file path is `90_Plans/Plan_YYYY-MM-DD_Research_<Topic>.md`. Then notify the user:
"I have created the research plan at `[plan file path]`. Please review and modify as needed, then confirm to proceed with execution."

# Phase 2: Launch Execution Agent (After User Confirmation)

Once the user confirms the plan, use the `run_command` tool to launch a **Ralph Loop**. Ralph will autonomously iterate through the plan's checklist, providing a much higher degree of reliability and iterative focus than a single subagent run.

```bash
/ralph:loop "You are the DeepOrbit Research Execution Agent. Your task is to execute the research plan at: 90_Plans/Plan_YYYY-MM-DD_Research_<Topic>.md

CRITICAL RULES for this iteration:
1. READ the plan file. Find the FIRST unchecked '- [ ]' task under 'Research Strategy' or 'Output Structure'.
2. Execute ONLY THAT TASK in this specific turn. For example:
   - If the task is to search the web, execute the search and read the results.
   - If the task is to create the main research note, draft 30_Research/<Area>/<Topic>/<Topic>.md.
   - If the task is to create an atomic Wiki concept, write it to 40_Wiki/<Category>/<ConceptName>.md.
3. Apply Obsidian formatting rules (CRITICAL):
   - Frontmatter MUST be at the very top (line 1), starting/ending with ---.
   - Main Note Frontmatter: type: reference, created: YYYY-MM-DD, area, tags, status: complete.
   - Wiki Notes: Keep atomic (1-3 paragraphs), use 99_System/Templates/Wiki_Template.md layout.
   - Related Links: Do NOT put related/see-also links in frontmatter. Put them in '## Related Reading' section at the BOTTOM of the note body.
4. After successfully completing the single task, modify the plan file tracking: change that specific '- [ ]' to '- [x]'.
5. End your turn. Ralph will automatically start the next iteration for the next unchecked task.
6. When ALL tasks in the plan are marked '- [x]', do the final linking (Append a link to 10_Diary/YYYY-MM-DD.md, archive the plan to 90_Plans/Archive/) and output exactly '<promise>RESEARCH_COMPLETE</promise>'." --completion-promise "RESEARCH_COMPLETE" --max-iterations 20
```

After the Ralph loop finishes (detects `RESEARCH_COMPLETE` promise), you (the Orchestrator) provide a final summary to the user:

## Research Summary: [Topic]

**Created:**
- Main Note: [[Topic]] located in 30_Research/<Area>/
- Knowledge Base Concepts: [[Concept1]], [[Concept2]], etc.
- Examples: [count] files located in examples/ (if any)

**Key Takeaways:**
1. Key point 1
2. Key point 2
3. Key point 3

**Next Steps:**
- [ ] Consolidate through practical exercises
- [ ] Apply to [[ProjectName]] (if applicable)
- [ ] Review in one week to reinforce memory


# Benefits of This Approach

1.  **Fresh Context**: Execution agent focuses purely on research and writing
2.  **Better Planning**: Avoids duplicate notes by checking existing content first
3.  **User Control**: User can adjust strategy before execution
4.  **Reduced Token Usage**: Research happens with clean context

# Edge Cases

-   **Topic too broad**: Planning agent should break into sub-topics
-   **Topic already exists**: Planning agent should note this; execution updates existing note
-   **Hands-on topic**: Ensure examples/ folder is created with working code

# Follow-up Protocol

If user asks for changes:

1.  Read the existing research note
2.  Make modifications directly - do not create duplicates
3.  Add new atomic concepts to Wiki if needed
4.  Update status if research is incomplete

## Rules

- Read `deeporbit.json` from the workspace root to determine the interaction language. Use this language for all your responses and generated note contents (e.g. `zh-CN`). **The Obsidian folder paths themselves will ALWAYS remain in English.**
- Use the `run_command` tool to execute `obsidian open path="<absolute_path>"` for every Markdown file you create or modify. See the `do.obsidian-open` skill for details.

