# DeepOrbit Site Assets

This file specifies every image placeholder on the home page (`site/src/components/HomePage.astro`).
Each placeholder is a `<div class="asset" data-asset="…">` in the markup. When an asset is produced,
replace the corresponding div with an `<img>` (or `<picture>`) referencing a file under `site/public/assets/`,
keeping the same `data-asset` attribute on the wrapper for traceability.

## Shared art direction

- **Mood:** calm, editorial, long-term. A personal knowledge system, not a sci-fi AI product.
- **Style:** flat isometric or fine-line illustration with soft grain; restrained geometry; no photorealism.
- **Palette (must match the site's CSS tokens exactly):**

| Token | Light hex | Usage |
|---|---|---|
| `--paper` | `#FAF9F6` | background |
| `--surface` | `#F2F0E9` | panels, card fills |
| `--ink` | `#23221E` | primary lines, text |
| `--body` | `#57544B` | secondary lines |
| `--muted` | `#8A867C` | tertiary detail |
| `--line` | `#DEDAD0` | hairlines, borders |
| `--accent` | `#D97757` | terracotta brand accent (sparingly) |
| `--accent-ink` | `#9C4529` | deep terracotta |
| `--sage` | `#5F7A5C` | growth / learning accent |
| `--sage-ink` | `#3F5A3D` | deep sage |

- **Avoid:** glassmorphism, neon glow, purple/cyan gradients, robot mascots, brains,
  floating 3D abstract blobs, stock-photo people, any text or letters inside the artwork,
  watermark-like logos, dark backgrounds (artwork must sit on `#FAF9F6` or transparent).
- **Export:** PNG with transparent background (or `#FAF9F6` background), 2× resolution,
  plus an SVG source if the tool supports it.

---

## 1. `data-asset="hero"` — hero main visual

- **Placement:** right half of the hero, aspect ratio **4:3.2** (e.g. 1600×1280 px @1x).
- **Subject:** an isometric illustration of a personal knowledge vault as a small orbital system:
  a tidy stack of Markdown documents at the center (shown as paper sheets with faint ruled lines,
  no readable text), orbited by small tokens representing tasks (checkbox squares),
  projects (folder shapes), and concepts (linked nodes). One orbit ring, thin hairline,
  with three satellite glyphs. A tiny terracotta bird (the brand mark, simple origami-like silhouette)
  perched on the top document.
- **Style:** flat isometric, fine `#23221E` outlines (1.5–2 px visual weight), fills limited to
  `#F2F0E9`, `#D97757`, `#5F7A5C`, and tints thereof; generous negative space.
- **Composition:** centered, the stack occupying ~55% of frame height; orbit ellipse tilted ~20°;
  nothing touching the edges; background transparent or `#FAF9F6`.
- **Prompt (feed to image model):**

> Flat isometric line illustration, warm editorial style: a neat stack of paper documents at the
> center (blank pages with faint ruled lines, no readable text), encircled by one thin orbital
> ellipse tilted 20 degrees. On the orbit: a small checkbox square, a small folder, and a small
> node-link glyph. A tiny origami-style bird silhouette in terracotta #D97757 perches on the top
> sheet. Fine dark-ink outlines (#23221E), fills only in off-white #F2F0E9, terracotta #D97757,
> and sage green #5F7A5C. Generous negative space, off-white background #FAF9F6, no text,
> no letters, no gradients, no glow, no shadows. Clean, calm, minimal.

---

## 2. `data-asset="dashboard"` — local dashboard illustration

- **Placement:** right column of the "deeporbit serve" section, aspect ratio **4:3** (e.g. 1600×1200 px @1x).
- **Subject:** a stylized local-first web dashboard window (browser chrome hinted, no URL text)
  showing a work-lifecycle board: four columns labeled only by colored dots (no words) —
  active, paused, done, archived — with a few abstract card rectangles in each;
  a small sidebar with a sparkline and a circular progress ring. One card being dragged between
  columns, motion implied by a short dashed trail.
- **Style:** flat UI illustration, hairline `#23221E` strokes, fills `#F2F0E9` / white,
  status dots in `#D97757`, `#8A867C`, `#5F7A5C`, `#DEDAD0`. Slight paper grain.
- **Composition:** window centered with even margins, ~80% of frame width; background transparent
  or `#FAF9F6`. Absolutely no legible text — UI copy must be abstract bars.
- **Prompt (feed to image model):**

> Flat minimal illustration of a desktop app window on an off-white #FAF9F6 background. The window
> shows a kanban-style board with four columns marked only by colored dots (terracotta #D97757,
> warm gray #8A867C, sage green #5F7A5C, pale beige #DEDAD0), each holding a few blank rounded
> card rectangles — no words, only abstract gray bars as fake text lines. A left sidebar with a
> tiny sparkline chart and one circular progress ring. One card is mid-drag between two columns,
> with a short dashed motion trail. Fine dark-ink outlines #23221E, fills #F2F0E9 and white,
> subtle paper grain. No readable text anywhere, no letters, no numbers, no glow, no gradients.

---

## 3. `data-asset="learner-profile"` — growth-loop illustration

- **Placement:** right column of the growth-loop section, aspect ratio **1:1.1** (e.g. 1200×1320 px @1x).
- **Subject:** a "learner profile" as a growing plant drawn in fine lines: roots formed from
  document-page shapes, a stem rising through three or four milestone nodes (small circles),
  and a canopy of linked concept nodes (a gentle knowledge-graph constellation).
  A thin upward spiral arrow (sage) wraps the stem, implying compounding growth.
- **Style:** fine-line botanical-meets-diagram illustration; strokes `#23221E`; accents only
  `#5F7A5C` (growth) with one small `#D97757` leaf or node as a brand echo; fills mostly empty
  (line art) with occasional `#F2F0E9` tint.
- **Composition:** vertical, plant centered, roots at bottom quarter, canopy at top quarter;
  transparent or `#FAF9F6` background.
- **Prompt (feed to image model):**

> Fine-line illustration, vertical composition: a stylized plant whose roots are made of small
> document-page shapes, a clean stem rising through three small milestone circles, and a canopy
> of gently linked constellation nodes (like a knowledge graph). A thin spiral arrow in sage green
> #5F7A5C winds upward around the stem, implying growth. Dark-ink line art #23221E, accents only
> in sage #5F7A5C with a single small terracotta #D97757 leaf. Mostly unfilled line art with a
> faint off-white #F2F0E9 tint, background off-white #FAF9F6 or transparent. Calm, elegant,
> editorial. No text, no letters, no faces, no gradients, no glow.

---

## Favicon

`site/public/favicon.svg` already exists — the terracotta DeepOrbit bird mark
(`#D97757` stroke on transparent), matching `--accent`. **Keep it as-is**; no new favicon work
is needed. The header logo in `BaseLayout.astro` inlines the same bird path, so brand marks stay
consistent. If the favicon is ever redrawn, reuse the exact path from
`site/src/layouts/BaseLayout.astro` and keep stroke color `#D97757`.
