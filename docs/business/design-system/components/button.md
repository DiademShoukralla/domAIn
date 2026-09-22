# Button

Primary interaction control. Four intents, three heights. One `primary` button per view — the single action that moves a turn forward (e.g. Composer send, OAuth connect confirm).

## Intents

| Intent | Classes | Use |
|--------|---------|-----|
| Primary | `btn btn--primary` | The one forward action per view. Accent fill, `text-on-solid` label. |
| Secondary | `btn btn--secondary` | Surface fill, `border-strong` outline. Confirmations, secondary paths. |
| Ghost | `btn btn--ghost` | Transparent, `text-secondary`. Low-weight actions (cancel, dismiss). |
| Danger | `btn btn--danger` | Danger fill, `text-on-solid`. Destructive actions (delete source). |

## Heights

| Size | Class | Height |
|------|-------|--------|
| Small | `btn--sm` | 28px (`layout-control-h-sm`) |
| Default | (none) | 36px (`layout-control-h`) |
| Large | `btn--lg` | 44px (`layout-control-h-lg`) |

Combine intent and size: `btn btn--primary btn--sm`.

## Markup

```html
<button type="button" class="btn btn--primary">Send</button>
<button type="button" class="btn btn--secondary btn--sm">Cancel</button>
<button type="button" class="btn btn--ghost">Dismiss</button>
<button type="button" class="btn btn--danger">Delete source</button>
```

## Behaviour

- Hover, active, focus, and disabled states follow the global elevation and focus rules.
- Disabled removes shadow and sets 45% opacity; hue unchanged.
- Icon + label: place Lucide icon before label, `aria-hidden="true"` on icon.

## Do not

- Place more than one `btn--primary` in the same view.
- Use `accent` fill for non-primary intents.
- Use danger for non-destructive actions.
