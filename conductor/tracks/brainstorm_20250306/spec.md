# Specification: Interactive Brainstorming Skill

## Overview
Implement a new agent skill `do-brainstorm` that allows users to have an interactive brainstorming session. This skill will help users explore ideas, refine concepts, and eventually transition to a project kickoff or knowledge capture.

## User Stories
- As a user, I want to start a brainstorming session on a vague idea.
- As a user, I want the agent to ask clarifying and provocative questions to expand my thinking.
- As a user, I want to be able to save the results of the brainstorm as a new project or a research note.

## Functional Requirements
- **Command**: `/do-brainstorm` or `do-brainstorm.toml`.
- **Interactive Dialogue**: The agent should engage in a multi-turn conversation.
- **Output Options**:
  - Create a new project note in `20_项目/`.
  - Create a research note in `30_研究/`.
  - Save to Inbox `00_收件箱/` for later processing.

## Technical Constraints
- Must follow the existing DeepOrbit skill structure (`skills/brainstorm/SKILL.md`).
- Must use the Socratic Inquiry style defined in `product-guidelines.md`.
- Must be implemented in Python if backend logic is required.
