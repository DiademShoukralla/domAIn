# PersonaMessage

A council member's opinion bubble. First-person voice. Includes persona mark, name, verdict badge, reasoning, and citations.

## Markup

```html
<article class="persona-message">
  <header class="persona-message__header">
    <span class="persona-message__mark persona-message__mark--ux mono-label">ux</span>
    <span class="persona-message__name persona-message__name--ux">UX</span>
    <span class="verdict-badge verdict--request-changes mono-label">request changes</span>
  </header>
  <div class="body">
    I would request changes because the current chunking strategy does not preserve section boundaries.
  </div>
  <!-- CodeCitation here -->
</article>
```

## Persona variants

| Persona | Mark class | Name class |
|---------|-----------|------------|
| UX | `persona-message__mark--ux` | `persona-message__name--ux` |
| Dev experience | `persona-message__mark--dx` | `persona-message__name--dx` |
| Business | `persona-message__mark--biz` | `persona-message__name--biz` |

## Do not

- Use persona colours as bubble background or left border.
- Write in third person ("The UX persona believes…").
