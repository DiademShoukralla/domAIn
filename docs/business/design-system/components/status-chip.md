# StatusChip

Source lifecycle indicator. Used in `SourceListItem` and anywhere a knowledge source status is shown.

## Values

| Value | Class | Semantic |
|-------|-------|----------|
| `pending` | `dom-status--pending` | info (same appearance as indexing) |
| `indexing` | `dom-status--indexing` | info |
| `ready` | `dom-status--ready` | success |
| `error` | `dom-status--error` | danger |

`pending` and `indexing` share one appearance on purpose — same info blue, same pulsing dot. The word carries the difference. Indexing may render a progress bar; pending never does.

## Markup

```html
<span class="dom-status-chip dom-status--pending">
  <span class="dom-status-chip__dot" aria-hidden="true"></span>
  <span class="mono-label">pending</span>
</span>

<span class="dom-status-chip dom-status--indexing">
  <span class="dom-status-chip__dot" aria-hidden="true"></span>
  <span class="mono-label">indexing</span>
  <span class="dom-status-chip__progress" aria-hidden="true"></span>
</span>
```

## Do not

- Give `pending` a neutral grey appearance — it shares indexing's info blue and pulsing dot.
- Render a progress bar on `pending`.
- Use `accent` for any status.
