# StatusChip

Source lifecycle indicator. Used in `SourceListItem` and anywhere a knowledge source status is shown.

## Values

| Value | Class | Semantic |
|-------|-------|----------|
| `pending` | `status--pending` | neutral |
| `indexing` | `status--indexing` | info |
| `ready` | `status--ready` | success |
| `error` | `status--error` | danger |

## Markup

```html
<span class="status-chip status--indexing">
  <span class="status-chip__dot" aria-hidden="true"></span>
  <span class="mono-label">indexing</span>
</span>
```

## Do not

- Add spinner icons that replace the status dot — the dot colour carries meaning.
- Use `accent` for any status.
