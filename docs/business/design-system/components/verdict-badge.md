# VerdictBadge

Inline chip showing a council verdict. Maps to GitHub PR review vocabulary.

## Values

| Value | Class | Appearance |
|-------|-------|------------|
| `approve` | `verdict--approve` | success semantic |
| `request_changes` | `verdict--request-changes` | danger semantic |
| `comment` | `verdict--comment` | neutral — `text-secondary` on `bg-sunken`, `border-strong` border |

`comment` is deliberately neutral, not blue. A third loud colour would flatten the two that are actual decisions.

## Markup

```html
<span class="verdict-badge verdict--approve mono-label">approve</span>
<span class="verdict-badge verdict--comment mono-label">comment</span>
```

## Do not

- Use `accent` or `info` colour for any verdict.
- Display custom verdict labels ("Needs work", "LGTM").
