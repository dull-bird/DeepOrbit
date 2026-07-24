# Methodology Map — Where Each Method Lives in DeepOrbit

> Design note. Researched 2026-07-21 from primary and canonical sources.
> The user constraint: methods stay **distinct** (不杂糅) — each governs one
> layer, with explicit handoffs. This document is the mentor skill's syllabus;
> `do.init` materializes it into `99_System/DeepOrbit/guides/methodology.md`.

## The one-paragraph answer

DeepOrbit's folder tree already *is* a method boundary map. GTD runs your
commitments (Inbox → tasks → agenda → weekly review). PARA files by
actionability (Projects/Research/Resources/Archive). Zettelkasten compounds
knowledge (Wiki). Atomic Habits keeps the rhythm (daily notes + cron). Adopting
more than one method *for the same layer* is what creates bloat — don't.

---

## GTD — David Allen (commitments & next actions)

**Core loop** (five steps): Capture everything → Clarify what it is and the
next physical action → Organize into lists → Reflect weekly → Engage.
Sources: [gettingthingsdone.com](https://gettingthingsdone.com/what-is-gtd/),
[Evernote PARA vs GTD](https://evernote.com/learn/para-vs-gtd-which-is-better-for-note-taking).

**Solves:** open loops. Anything with a *next action* belongs here.

**Maps to DeepOrbit:**

- Capture → `00_Inbox/` (+ `Todos.md`), any agent chat, quick notes.
- Clarify/Organize → `/do:todo` (stable `^do-*` IDs), `/do:kickoff` for
  inbox items that are really projects.
- Reflect → the Weekly Review recipe (`99_System/Recipes/Weekly Review.md`),
  `/do:archive` lifecycle review.
- Engage → `/do:agenda` (overdue/today/upcoming/unscheduled).

**Deliberately not adopted:** context lists (@home/@computer — tags can do it,
but we don't push them; most agent-assisted work is context-free), the full
43-folder tickler file (cron jobs replace it).

**Boundary:** GTD owns *verbs* (things to do). The moment an item has no next
action, it leaves GTD's layer — file it via PARA or distill it via Zettelkasten.

## PARA — Tiago Forte (filing by actionability)

**Core loop:** file everything into Projects (active outcomes), Areas
(ongoing standards), Resources (future interest), Archives (inactive) — by
*how actionable* it is, not by topic. Sources:
[fortelabs.com PARA](https://fortelabs.com/blog/para/),
[BASB](https://www.buildingasecondbrain.com/).

**Solves:** "where does this file go" hesitation and stale project lists.

**Maps to DeepOrbit:** the tree is nearly native PARA —

| PARA | DeepOrbit |
|---|---|
| Projects | `20_Projects/` with `status: active|paused|done` |
| Areas | `30_Research/` (ongoing interests, no end date) |
| Resources | `50_Resources/` |
| Archives | `99_System/Archive/` via `deeporbit archive` |

The lifecycle CLI (`status/pause/resume/done/archive`) is PARA's flow made
deterministic; `99_System/Bases/Work Status.base` is its dashboard.

**Deliberately not adopted:** Forte's "reorganize on every project start" —
too much churn; we re-file only at lifecycle transitions. CODE (Capture,
Organize, Distill, Express) overlaps GTD capture + Zettel distillation; we
cite it as framing, not as a separate workflow.

**Boundary:** PARA decides *location*; it never decides what to *do* (GTD) or
what an idea *means* (Zettelkasten).

## Zettelkasten / 卡片笔记 — Luhmann via Sönke Ahrens (knowledge compounding)

**Core loop:** fleeting notes → literature notes → permanent **atomic** notes
in your own words, densely interlinked; writing *is* thinking. Sources:
[Ahrens, *How to Take Smart Notes*](https://takesmartnotes.com/),
[zettelkasten.de](https://zettelkasten.de/posts/overview/).

**Solves:** notes that pile up but never compound into understanding.

**Maps to DeepOrbit:**

- Fleeting → `00_Inbox`; literature → `60_Notes` (+ `/do:note-summary`).
- Permanent atomic → `40_Wiki/<Concept>.md` — one idea per note, own words,
  wikilinks both ways (`/do:fix-links` finds ghosts).
- Compounding → `/do:dream` pass 1 (pattern promotion) turns repeated themes
  into Wiki notes; `40_Wiki` is method-pure: no tasks, no project state.

**Deliberately not adopted:** Luhmann's alphanumeric branching IDs (filenames
+ links suffice), mandatory daily Zettel quotas (ceremony without payoff).

**Boundary:** Wiki notes are *timeless*; if a note is about a date or a
deliverable it doesn't belong to this layer.

## Atomic Habits — James Clear (behavior rhythm)

**Core loop:** make it obvious / attractive / easy / satisfying (four laws);
implementation intentions ("When X, I will Y"); habit stacking; never miss
twice. Sources: [jamesclear.com/atomic-habits](https://jamesclear.com/atomic-habits),
[book notes](https://thereadwellpodcast.com/book-notes-atomic-habits-by-james-clear/).

**Solves:** the system decaying because reviews don't happen.

**Maps to DeepOrbit:**

- Cue → cron jobs (`deeporbit cron add …`) + agent-runtime schedulers: daily
  note, dream pass, weekly review fire on time, not on willpower.
- Easy → `/do:daily` opens today pre-assembled; recipes turn multi-step
  routines into one command.
- Satisfying → `/do:recap` and dream reports make progress visible.
- Implementation intentions → stored as `note:` steps inside recipes
  ("when Friday, run Weekly Review").

**Deliberately not adopted:** streak counters/scoreboards — they optimize the
metric, not the work. We track completion, not streaks.

**Boundary:** habits govern *when* workflows run, never *what* they contain.

## Weekly review & interstitial journaling (supporting practices)

- **Weekly review** is GTD's reflect step and the single highest-leverage
  habit; it is packaged as the `Weekly Review` recipe so it can be scheduled,
  not remembered.
- **Interstitial journaling** (one timestamped line between tasks) fits
  `10_Diary/` as freeform entries under the daily note; no dedicated tooling —
  adding any would be ceremony.

## The handoff contract (one rule per boundary)

1. Inbox → GTD clarify: every item leaves the inbox as a **task**, a
   **project**, a **resource**, or **trash**. Nothing stays "for later".
2. GTD → PARA: a task with a multi-step outcome becomes a `20_Projects` note
   (`/do:kickoff`); a finished project is archived, not deleted.
3. Any layer → Zettelkasten: an idea worth keeping is rewritten as one atomic
   Wiki note in your own words and linked — never moved raw.
4. Habits → everything: cron only *triggers* workflows; it never changes their
   content.

## Sources

- Allen, GTD: https://gettingthingsdone.com/what-is-gtd/
- Forte, PARA: https://fortelabs.com/blog/para/ · BASB: https://www.buildingasecondbrain.com/
- Ahrens: https://takesmartnotes.com/ · https://zettelkasten.de/posts/overview/
- Clear: https://jamesclear.com/atomic-habits
- Comparison reads: https://evernote.com/learn/para-vs-gtd-which-is-better-for-note-taking · https://yourstory.com/2026/01/choose-right-productivity-system-gtd-para-zettelkasten-second-brain
