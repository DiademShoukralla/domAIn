# SourceListItem

One row in the knowledge-source rail. Shows source name, external reference, and lifecycle status.

## Status model

Exactly four status values. Do not invent additional states.

| Value | Display | Semantic class |
|-------|---------|----------------|
| `pending` | Pending | `status--pending` |
| `indexing` | Indexing | `status--indexing` |
| `ready` | Ready | `status--ready` |
| `error` | Error | `status--error` |

Pass the raw status string from the API. CSS handles uppercase display.

## Markup

```html
<div class="source-list-item">
  <svg class="source-list-item__icon" aria-hidden="true"><!-- Lucide icon --></svg>
  <div class="source-list-item__body">
    <div class="source-list-item__title">domAIn</div>
    <div class="source-list-item__meta">DiademShoukralla/domAIn</div>
  </div>
  <span class="status-chip status--ready">
    <span class="status-chip__dot" aria-hidden="true"></span>
    <span class="mono-label">ready</span>
  </span>
</div>
```

## Error state

When status is `error`, show `status_message` from the API below the meta line in `caption` style:

```html
<div class="caption">Reconnect the workspace to resume indexing.</div>
```

## Do not

- Add a fifth status (e.g. "syncing", "paused", "stale").
- Use `accent` colour for any status chip.
