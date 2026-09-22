# SourceListItem

One row in the knowledge-source rail. Shows source name, external reference, and lifecycle status.

## Status model

Exactly four status values. Do not invent additional states.

| Value | Display | Semantic class | Notes |
|-------|---------|----------------|-------|
| `pending` | Pending | `dom-status--pending` | Same info blue + pulsing dot as indexing; no progress bar |
| `indexing` | Indexing | `dom-status--indexing` | Info blue + pulsing dot + progress bar |
| `ready` | Ready | `dom-status--ready` | |
| `error` | Error | `dom-status--error` | |

Pass the raw status string from the API. CSS handles uppercase display.

## Markup

```html
<div class="dom-source-list-item">
  <svg class="dom-source-list-item__icon" aria-hidden="true"><!-- Lucide icon --></svg>
  <div class="dom-source-list-item__body">
    <div class="dom-source-list-item__title">domAIn</div>
    <div class="dom-source-list-item__meta">DiademShoukralla/domAIn</div>
  </div>
  <span class="dom-status-chip dom-status--ready">
    <span class="dom-status-chip__dot" aria-hidden="true"></span>
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
- Show a progress bar when status is `pending`.
