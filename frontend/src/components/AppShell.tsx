import { useState } from "react";
import { getStoredApiKey, setStoredApiKey } from "../lib/session";
import { resolveAppView } from "../lib/routing";
import { ChatApp } from "./ChatApp";
import { ConnectionsView } from "./ConnectionsView";

export function AppShell() {
  const [apiKey, setApiKey] = useState(getStoredApiKey);
  const [apiKeyDraft, setApiKeyDraft] = useState(getStoredApiKey);
  const [error, setError] = useState<string | null>(null);
  const view = resolveAppView();

  const handleSaveApiKey = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = apiKeyDraft.trim();
    if (!trimmed) {
      setError("Enter an API key to connect.");
      return;
    }
    setStoredApiKey(trimmed);
    setApiKey(trimmed);
    setError(null);
  };

  if (!apiKey) {
    return (
      <main className="dom-app">
        <section className="dom-setup layout-thread">
          <h1 className="dom-setup__title">Connect to domAIn</h1>
          <p className="body">Enter your API key to open the chat session.</p>
          <form className="dom-setup__form" onSubmit={handleSaveApiKey}>
            <label className="label" htmlFor="api-key">
              API key
            </label>
            <input
              id="api-key"
              className="dom-setup__input"
              type="password"
              autoComplete="off"
              value={apiKeyDraft}
              onChange={(event) => setApiKeyDraft(event.target.value)}
            />
            <button type="submit" className="dom-btn dom-btn--primary">
              Connect
            </button>
          </form>
          {error ? <p className="dom-error caption">{error}</p> : null}
        </section>
      </main>
    );
  }

  return (
    <main className="dom-app">
      {view === "connections" ? <ConnectionsView apiKey={apiKey} /> : <ChatApp apiKey={apiKey} />}
    </main>
  );
}
