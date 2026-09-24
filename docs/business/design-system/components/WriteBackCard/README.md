# WriteBackCard

Operator-facing write-back control nested in a completed `dom-chair-block` footer. One card per council result. Drives propose → refine → confirm against the persisted assistant message id.

## Placement

Always inside `dom-chair-block__footer` on a completed council result. Never a separate panel or modal.

```html
<article class="dom-chair-block">
  <header class="dom-chair-block__header">...</header>
  <div class="body-lg">...</div>
  <footer class="dom-chair-block__footer">
    <div class="dom-write-back-card">...</div>
  </footer>
</article>
```

## States

| State | Markup | Behaviour |
|-------|--------|-----------|
| Untriggered | `dom-btn dom-btn--secondary dom-btn--sm` "Propose write-back" | `POST /chat/messages/{message_id}/write-back` using the assistant message's persisted id |
| Proposed | Plain list of planned actions, feedback field, Refine + Confirm | Refine calls `PATCH /write-back-proposals/{id}`; Confirm calls `POST /write-back-proposals/{id}/confirm` |
| Empty plan | Plain text "No follow-up action needed." | Both `needs_doc_update` and `needs_roadmap_item` false — no Confirm button |
| Executing | Confirm uses Button disabled treatment | Awaiting confirm response |
| Executed | Plan list replaced by result links with `dom-write-back-card__check` icon | Read-only; links from `execution_results` |
| Failed | `dom-write-back-card__error` + secondary "Retry" | Plan and feedback remain visible underneath |

## Markup

```html
<div class="dom-write-back-card">
  <ul class="dom-write-back-card__list">
    <li>Update docs/adr/0002-tech-stack.md</li>
    <li>Create Linear roadmap item</li>
  </ul>
  <label class="dom-write-back-card__field">
    <span class="caption">Feedback</span>
    <textarea class="dom-write-back-card__input" rows="2"></textarea>
  </label>
  <div class="dom-write-back-card__actions">
    <button type="button" class="dom-btn dom-btn--secondary dom-btn--sm">Refine</button>
    <button type="button" class="dom-btn dom-btn--primary dom-btn--sm">Confirm</button>
  </div>
</div>
```

Executed state:

```html
<div class="dom-write-back-card dom-write-back-card--executed">
  <ul class="dom-write-back-card__list">
    <li class="dom-write-back-card__result">
      <svg class="dom-write-back-card__check" aria-hidden="true"></svg>
      <a href="https://github.com/owner/repo/pull/1" target="_blank" rel="noreferrer">Update docs/adr/0002-tech-stack.md</a>
    </li>
  </ul>
</div>
```

## Backend prerequisite

`ChatResponse` (WebSocket final frame) must include `id: UUID` — the persisted `chat_messages.id` for the assistant row. `process_message` persists the assistant message before constructing the response and attaches the real id. The frontend must use this id for write-back, not a client-generated placeholder.

`WriteBackProposalOut` includes `execution_results` (PR and Linear URLs) after confirm so executed state survives page reload.

## Behaviour

- Read initial state from `write_back_proposal` on chat history load.
- Exactly one card per chair block; never re-offer the propose trigger once a proposal exists.
- Refine replaces the plan list in place — never a new card or thread row.
- Confirm is the only `dom-btn--primary` inside the card.
- Error state never hides the plan.
- Once `status` is `executed`, the card is permanently read-only.

## Do not

- Mount WriteBackCard outside `dom-chair-block__footer`.
- Call write-back endpoints with a client-generated message id.
- Add a second primary button inside the card.
- Hide the plan on confirm failure.
