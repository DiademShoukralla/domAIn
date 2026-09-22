# CitationBlock

Evidence snippet linking back to a knowledge-layer chunk.

## Markup

```html
<div class="citation-block">
  <div class="citation-block__source">docs/adr/0002-tech-stack.md · chunk 4</div>
  <pre class="citation-block__body">Use a simple default chunking strategy for v1:
- Split on paragraph/section boundaries where possible.</pre>
</div>
```

## Do not

- Truncate citation bodies without an expand affordance.
- Omit the source path — citations must be traceable.
