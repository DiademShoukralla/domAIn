# Button

Primary interaction control. Four intents, three heights. One `primary` button per view — the single action that moves a turn forward (e.g. Composer send, OAuth connect confirm).

## Intents

| Intent | Classes | Use |
|--------|---------|-----|
| Primary | `dom-btn dom-btn--primary` | The one forward action per view. Accent fill, `text-on-solid` label. |
| Secondary | `dom-btn dom-btn--secondary` | Surface fill, `border-strong` outline. Confirmations, secondary paths. |
| Ghost | `dom-btn dom-btn--ghost` | Transparent, `text-secondary`. Low-weight actions (cancel, dismiss). |
| Danger | `dom-btn dom-btn--danger` | Danger fill, `text-on-solid`. Destructive actions (delete source). |

## Heights

| Size | Class | Height |
|------|-------|--------|
| Small | `dom-btn--sm` | 28px (`layout-control-h-sm`) |
| Default | (none) | 36px (`layout-control-h`) |
| Large | `dom-btn--lg` | 44px (`layout-control-h-lg`) |

Combine intent and size: `dom-btn dom-btn--primary dom-btn--sm`.

## Markup

```html
<button type="button" class="dom-btn dom-btn--primary">Send</button>
<button type="button" class="dom-btn dom-btn--secondary dom-btn--sm">Cancel</button>
<button type="button" class="dom-btn dom-btn--ghost">Dismiss</button>
<button type="button" class="dom-btn dom-btn--danger">Delete source</button>
```

## Behaviour

- Hover, active, focus, and disabled states follow the global elevation and focus rules.
- Disabled removes shadow and sets 45% opacity; hue unchanged.
- Icon + label: place Lucide icon before label, `aria-hidden="true"` on icon.

## Do not

- Place more than one `dom-btn--primary` in the same view.
- Use `accent` fill for non-primary intents.
- Use danger for non-destructive actions.
