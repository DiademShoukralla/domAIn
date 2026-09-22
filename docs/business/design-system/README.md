Three seats debate. One recommendation ships.

domAIn is a developer-facing tool where an engineer or PM asks a question and either gets a direct answer out of an indexed knowledge base, or watches a council of three personas argue and a chair synthesise them. The interface has one job: make it obvious, at a glance, *who is speaking*, *what they decided*, and *what evidence it rests on*. Everything below serves that.

This system ships tokens and a stylesheet, not a JavaScript package. Load `tokens.css`, then `components/bundle.css`, and use the documented classes. Every component's markup contract is in its own card.

## Voice and content

- Write in plain declarative sentences. The audience is technical and is evaluating a proposal, not being sold one.
- Name the thing. `Request changes`, not `Needs work`. `Indexing`, not `Working on it`. Never soften a verdict.
- Use sentence case everywhere except the three uppercase roles: `overline` eyebrows, `mono-label` badge and status words, and persona marks. Those are uppercased by CSS — the strings you pass stay sentence case.
- The personas have names and speak in the first person; the chair does not. The chair states a recommendation and the reason for it in one paragraph, and never says "I".
- No emoji. No exclamation marks. Hedging is allowed only when the system is genuinely uncertain, and then it says why.
- Errors say what happened and what to do next, in one sentence: "Reconnect the workspace to resume indexing."

## Colour

The palette is a warm-neutral greyscale with exactly one brand hue and three semantics. Everything else is a tint of those.

- `accent` (amber) is the brand and the only warm hue in the UI. Use it for primary actions, links, the chair's band, the council-is-working pulse, and any advisory that is not a verdict or a source status — stale index, quota, rate limit. **Never use `accent` for a verdict or a source state.** That separation is what lets the amber mean "the system wants your attention" everywhere it appears.
- `success`, `danger` and `info` are the three semantics: approve / ready, request changes / error, indexing / informational. Each has a `-surface` for tinted grounds and a `-border` that clears 3:1.
- `persona-ux`, `persona-dx` and `persona-biz` identify the three seats. They are lower in chroma than the semantics and sit at hues between them, so a persona mark never reads as a status. They appear only on the mark and the speaker's name — never as a bubble fill, never as a border down the side of a message.
- `persona-chair` aliases `accent` on purpose: the synthesis is the product speaking, not a fourth opinion.
- Backgrounds go `bg-canvas` (the page) → `bg-surface` (panels and bubbles) → `bg-raised` (the chair block, popovers) → `bg-sunken` (code, wells, the user's own message). In Light, `bg-raised` equals `bg-surface` and elevation comes from `shadow-md`; in Dark it is a lighter surface. Never both.
- Borders: `border-subtle` for hairlines that only separate, `border-default` for panel edges, `border-strong` for any edge that carries meaning — buttons, inputs, the composer, status chips.
- No gradients anywhere. No blue-to-violet anything. If a surface needs to stand out, change the surface token or add elevation, not a gradient.

## Typography

- Set everything in `sans` (Inter) except code, paths, badge and status words, and metadata, which are `mono` (JetBrains Mono). Load both from the host application; this system ships no font files.
- Body copy is `body` (15/24). The chair alone gets `body-lg` (16/26), because it is the one block people read end to end.
- `label-strong` for a persona name or a source title; `label` for button and toggle text; `caption` for timestamps.
- `code` for inline code inside prose, `code-block` (13/22) for citation bodies — the extra leading is for line numbers and the highlight row — and `code-sm` for paths and meta lines.
- `mono-label` (11px, +0.06em, uppercased) is the system's signature detail: it marks everything machine-stated — persona marks, verdicts, statuses, counts — and separates it from human-written prose. Do not use it for prose.
- One `display-*` per screen at most. A thread has no display type at all.

## Spacing and layout

- Everything sits on the 4px grid: `space-1` through `space-16`, no values in between.
- `space-4` is the default padding inside a bubble, card or panel. `space-6` is the gap between messages; `space-8` after a chair block.
- Widths come from the layout tokens: `layout-thread-max` (768px) for the thread column and the chair, `layout-bubble-max` (620px) for every other message, `layout-rail-w` (300px) for the knowledge-source rail, `layout-gutter` (24px) between them.
- Control heights are `layout-control-h-sm` / `-h` / `-h-lg` (28 / 36 / 44). A verdict badge is 28px so it lines up with a small button in the same row.
- Radii: `radius-xs` on badges, chips and persona marks; `radius-sm` on controls; `radius-md` on bubbles, citations and cards; `radius-lg` on the chair block, composer and panels; `radius-pill` only on status dots.

## Elevation, borders and states

- One shadow level per stacking context. `shadow-xs` on resting buttons, `shadow-sm` on cards and the composer, `shadow-md` on the chair block and popovers, `shadow-lg` on modals.
- Hover is `bg-hover`, pressed is `bg-active`, selected is `bg-selected` (warm, because selection is an accent state).
- Focus is one thing everywhere: a 2px solid `focus-ring` outline at `layout-focus-offset` from the control edge. Never a shadow, never a colour change alone, never removed.
- Disabled is 45% opacity with the shadow removed. The hue does not change, so the intent stays readable.

## Iconography

Use Lucide (lucide.dev) at `layout-icon` (16px) with a 1.5px stroke and `currentColor`, `layout-icon-sm` (14px) inside badges and chips, `layout-icon-lg` (20px) in the header and empty states. No icon files ship with this system. Icons are decorative wherever a text label is present: mark them `aria-hidden="true"` and let the label carry the meaning.

## Status and verdict language

Three verdicts and four source states. Never reuse `accent` for any of these.

- `comment` is deliberately neutral, not blue — a third loud colour would flatten the two that are actual decisions (`approve`, `request_changes`).
- `pending` and `indexing` share one appearance on purpose — same info blue, same pulsing dot. The word carries the difference; the progress bar is what makes a running job look different from a queued one. Pending never renders a progress bar.

| Kind | Value | Semantic | CSS class |
|------|-------|----------|-----------|
| Verdict | `approve` | success | `verdict--approve` |
| Verdict | `request_changes` | danger | `verdict--request-changes` |
| Verdict | `comment` | neutral (`text-secondary` on `bg-sunken`) | `verdict--comment` |
| Source status | `pending` | info (same as indexing) | `status--pending` |
| Source status | `indexing` | info | `status--indexing` |
| Source status | `ready` | success | `status--ready` |
| Source status | `error` | danger | `status--error` |

Pass the string value as sentence case in markup (`approve`, `request changes`, `indexing`). CSS uppercases display via `mono-label`.

## Components

| Component | Card | Purpose |
|-----------|------|---------|
| Button | [components/button.md](components/button.md) | Primary, secondary, ghost, and danger actions. |
| Composer | [components/composer.md](components/composer.md) | Message input. **No routing toggle.** |
| SourceListItem | [components/source-list-item.md](components/source-list-item.md) | One row in the knowledge-source rail. Four status states. |
| PersonaMessage | [components/persona-message.md](components/persona-message.md) | A council member's opinion bubble. |
| ChairBlock | [components/chair-block.md](components/chair-block.md) | Synthesis and overall verdict. |
| VerdictBadge | [components/verdict-badge.md](components/verdict-badge.md) | Inline verdict chip. |
| StatusChip | [components/status-chip.md](components/status-chip.md) | Source lifecycle indicator. |
| CodeCitation | [components/code-citation.md](components/code-citation.md) | Evidence snippet with line numbers, syntax tokens, hit row. |
| RetrievalMessage | [components/retrieval-message.md](components/retrieval-message.md) | Direct answer from simple retrieval. |

## Implementation constraints

These two rules come from product architecture and must not be violated in UI implementation:

1. **The Composer has no routing toggle.** The user never selects Simple vs. Council mode. Intent routing is backend-only (see ADR 0005).
2. **`SourceListItem` status uses exactly four values:** `pending`, `indexing`, `ready`, `error`. No additional states, no compound labels.
