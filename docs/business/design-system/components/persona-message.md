# PersonaMessage

A council member's opinion bubble. First-person voice. Includes persona mark, name, verdict badge, reasoning, and citations.

## Markup

```html
<article class="dom-persona-message">
  <header class="dom-persona-message__header">
    <span class="dom-persona-message__mark dom-persona-message__mark--ux mono-label">ux</span>
    <span class="dom-persona-message__name dom-persona-message__name--ux">UX</span>
    <span class="dom-verdict dom-verdict--request-changes mono-label">request changes</span>
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
| UX | `dom-persona-message__mark--ux` | `dom-persona-message__name--ux` |
| Dev experience | `dom-persona-message__mark--dx` | `dom-persona-message__name--dx` |
| Business | `dom-persona-message__mark--biz` | `dom-persona-message__name--biz` |

## Do not

- Use persona colours as bubble background or left border.
- Write in third person ("The UX persona believes…").
