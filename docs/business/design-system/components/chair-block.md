# ChairBlock

The synthesis block. States a recommendation and the reason for it in one paragraph. Never uses first person.

## Markup

```html
<article class="dom-chair-block">
  <header class="dom-chair-block__header">
    <span class="dom-chair-block__label">Recommendation</span>
    <span class="dom-verdict dom-verdict--comment mono-label">comment</span>
  </header>
  <div class="body-lg">
    The council recommends commenting rather than blocking: chunking can remain simple for v1 while the ADR documents a migration path to semantic splitting if retrieval quality degrades on code files.
  </div>
</article>
```

## Voice

- Third person or imperative. Never "I recommend" or "I think".
- One paragraph for synthesis. Verdict badge carries the discrete decision.

## Do not

- Give the chair a persona mark or persona colour — it uses `accent` via `persona-chair` alias.
- Split synthesis into bullet points unless the content is genuinely a list.
