# CodeCitation

Evidence snippet from a knowledge-layer chunk. Shows source path, per-line numbering, syntax token colours, and a hit row marking the line retrieval matched.

## Markup

```html
<figure class="dom-code-citation">
  <figcaption class="dom-code-citation__source code-sm">
    docs/adr/0002-tech-stack.md · lines 88–92
  </figcaption>
  <div class="dom-code-citation__scroll">
    <ol class="dom-code-citation__lines">
      <li class="dom-code-citation__line" data-line="88">
        <span class="dom-tok-com"># Chunking strategy</span>
      </li>
      <li class="dom-code-citation__line dom-code-citation__line--hit" data-line="89">
        <span class="dom-tok-kw">Use</span><span class="dom-tok-pun"> a </span><span class="dom-tok-kw">simple</span><span class="dom-tok-pun"> </span><span class="dom-tok-kw">default</span><span class="dom-tok-pun"> chunking strategy for v1:</span>
      </li>
      <li class="dom-code-citation__line" data-line="90">
        <span class="dom-tok-pun">- Split on paragraph/section boundaries where possible.</span>
      </li>
    </ol>
  </div>
</figure>
```

## Syntax tokens

| Class | Aliases | Use |
|-------|---------|-----|
| `dom-tok-com` | `syntax-comment` → `text-muted` | Comments, docstrings |
| `dom-tok-kw` | `syntax-keyword` → `info` | Keywords, directives |
| `dom-tok-str` | `syntax-string` → `success` | String literals |
| `dom-tok-num` | `syntax-number` → `accent` | Numeric literals |
| `dom-tok-pun` | `syntax-punct` → `text-secondary` | Punctuation, operators, plain text |

## Hit row

Mark the line retrieval actually matched with `dom-code-citation__line--hit`:

- Background: `accent-surface`
- Left rule: 2px inset `accent` (via `box-shadow: inset 2px 0 0`)

Only one hit row per citation unless the chunk spans multiple matched lines.

## Line numbers

Set `data-line` on each `dom-code-citation__line`. CSS renders the gutter via `::before { content: attr(data-line) }`. Use `code-block` leading (13/22).

## Do not

- Render as a plain `<pre>` without line numbers or token spans.
- Omit the source path in the figcaption.
- Use info blue for comment verdict badges — comment is neutral, not semantic blue.
