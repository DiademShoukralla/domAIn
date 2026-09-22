# Composer

The message input at the bottom of the chat thread. Sends user messages to the unified chat endpoint. The backend supervisor classifies intent — there is no mode selector in this component.

## Constraints

- **No routing toggle.** Do not add a Simple/Council switch, segmented control, or any UI that lets the user pick a chat mode.
- One text input and one submit button.

## Markup

```html
<form class="composer" role="form" aria-label="Send a message">
  <textarea
    class="composer__input"
    rows="1"
    placeholder="Ask a question or submit a proposal for review"
    aria-label="Message"
  ></textarea>
  <button type="submit" class="composer__submit" aria-label="Send">
    Send
  </button>
</form>
```

## Behaviour

- Submit on Enter (Shift+Enter for newline).
- Disable submit while a response is streaming.
- Auto-grow textarea up to 4 lines, then scroll.
- Focus ring on the composer container when the input is focused.

## Do not

- Add a mode toggle, tab bar, or dropdown for routing.
- Add emoji picker or exclamation-mark placeholder text.
