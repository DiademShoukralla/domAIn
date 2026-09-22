# CodeCitation

Evidence snippet from a knowledge-layer chunk. Shows source path, per-line numbering, syntax token colours, and a hit row marking the line retrieval matched.

## Markup

```html
<figure class="code-citation">
  <figcaption class="code-citation__source code-sm">
    docs/adr/0002-tech-stack.md · lines 88–92
  </figcaption>
  <div class="code-citation__scroll">
    <ol class="code-citation__lines">
      <li class="code-citation__line" data-line="88">
        <span class="tok-com"># Chunking strategy</span>
      </li>
      <li class="code-citation__line code-citation__line--hit" data-line="89">
        <span class="tok-kw">Use</span><span class="tok-pun"> a </span><span class="tok-kw">simple</span><span class="tok-pun"> </span><span class="tok-kw">default</span><span class="tok-pun"> chunking strategy for v1:</span>
      </li>
      <li class="code-citation__line" data-line="90">
        <span class="tok-pun">- Split on paragraph/section boundaries where possible.</span>
      </li>
    </ol>
  </div>
</figure>
```

## Syntax tokens

| Class | Aliases | Use |
|-------|---------|-----|
| `tok-com` | `syntax-comment` → `text-muted` | Comments, docstrings |
| `tok-kw` | `syntax-keyword` → `info` | Keywords, directives |
| `tok-str` | `syntax-string` → `success` | String literals |
| `tok-num` | `syntax-number` → `accent` | Numeric literals |
| `tok-pun` | `syntax-punct` → `text-secondary` | Punctuation, operators, plain text |

## Hit row

Mark the line retrieval actually matched with `code-citation__line--hit`:

- Background: `accent-surface`
- Left rule: 2px inset `accent` (via `box-shadow: inset 2px 0 0`)

Only one hit row per citation unless the chunk spans multiple matched lines.

## Line numbers

Set `data-line` on each `code-citation__line`. CSS renders the gutter via `::before { content: attr(data-line) }`. Use `code-block` leading (13/22).

## Do not

- Render as a plain `<pre>` without line numbers or token spans.
- Omit the source path in the figcaption.
- Use info blue for comment verdict badges — comment is neutral, not semantic blue.
