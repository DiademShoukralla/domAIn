# VerdictBadge

Inline chip showing a council verdict. Maps to GitHub PR review vocabulary.

## Values

| Value | Class |
|-------|-------|
| `approve` | `verdict--approve` |
| `request_changes` | `verdict--request-changes` |
| `comment` | `verdict--comment` |

## Markup

```html
<span class="verdict-badge verdict--approve mono-label">approve</span>
```

## Do not

- Use `accent` colour for any verdict.
- Display custom verdict labels ("Needs work", "LGTM").
