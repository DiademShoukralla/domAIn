import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchChatHistory,
  fetchSourceCount,
  historyToThreadItems,
} from "../lib/api";
import {
  applyStatusUpdate,
  councilItemFromResponse,
  createInitialPendingState,
  directItemFromResponse,
  OPTIMISTIC_STATUS,
} from "../lib/councilState";
import {
  getOrCreateSessionId,
  getStoredApiKey,
  setStoredApiKey,
} from "../lib/session";
import type { IncomingFrame, ThreadItem } from "../types/chat";
import { isChatResponse, isChatStatusUpdate } from "../types/chat";
import { useChatWebSocket } from "../hooks/useChatWebSocket";
import { ChatThread } from "./ChatThread";
import { Composer } from "./ChatMessage";

export function ChatApp() {
  const [sessionId] = useState(getOrCreateSessionId);
  const [apiKey, setApiKey] = useState(getStoredApiKey);
  const [apiKeyDraft, setApiKeyDraft] = useState(getStoredApiKey);
  const [items, setItems] = useState<ThreadItem[]>([]);
  const [readySourceCount, setReadySourceCount] = useState<number | null>(null);
  const [awaitingResponse, setAwaitingResponse] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  const activeCouncilIdRef = useMemo(() => ({ current: null as string | null }), []);

  const refreshSourceCount = useCallback(async (key: string) => {
    try {
      const count = await fetchSourceCount(key);
      setReadySourceCount(count);
    } catch {
      setReadySourceCount(0);
    }
  }, []);

  const loadHistory = useCallback(async (key: string) => {
    const history = await fetchChatHistory(sessionId, key);
    setItems(historyToThreadItems(history.messages));
    setHistoryLoaded(true);
  }, [sessionId]);

  useEffect(() => {
    if (!apiKey) {
      setHistoryLoaded(false);
      return;
    }
    void Promise.all([loadHistory(apiKey), refreshSourceCount(apiKey)]).catch((loadError) => {
      setError(loadError instanceof Error ? loadError.message : "Failed to load chat history.");
      setHistoryLoaded(true);
    });
  }, [apiKey, loadHistory, refreshSourceCount]);

  const handleIncomingStatus = useCallback(
    (frame: IncomingFrame) => {
      if (!isChatStatusUpdate(frame)) {
        return;
      }
      const councilId = activeCouncilIdRef.current;
      if (!councilId) {
        return;
      }
      setItems((current) =>
        current.map((item) => {
          if (item.kind !== "council" || item.id !== councilId || item.phase !== "pending") {
            return item;
          }
          return {
            ...item,
            pending: applyStatusUpdate(item.pending, frame),
          };
        }),
      );
    },
    [activeCouncilIdRef],
  );

  const { connected, sendMessage } = useChatWebSocket({
    apiKey,
    enabled: Boolean(apiKey),
    onStatus: handleIncomingStatus,
    onError: setError,
  });

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

  const handleSend = async (content: string) => {
    if (!apiKey || awaitingResponse) {
      return;
    }

    const userItem: ThreadItem = {
      id: crypto.randomUUID(),
      kind: "user",
      content,
    };

    const councilId = crypto.randomUUID();
    activeCouncilIdRef.current = councilId;

    setItems((current) => [
      ...current,
      userItem,
      {
        id: councilId,
        kind: "council",
        phase: "pending",
        pending: {
          ...createInitialPendingState(),
          supervisorStatus: OPTIMISTIC_STATUS,
        },
      },
    ]);
    setAwaitingResponse(true);
    setError(null);

    try {
      const response = await sendMessage({ session_id: sessionId, content });

      if (isChatResponse(response) && response.response_kind === "council_result") {
        setItems((current) =>
          current.flatMap((item) => {
            if (item.id === councilId) {
              return [councilItemFromResponse(response, councilId)];
            }
            return [item];
          }),
        );
      } else if (isChatResponse(response)) {
        const directItem = directItemFromResponse(response, crypto.randomUUID());
        setItems((current) => [
          ...current.filter((item) => item.id !== councilId),
          directItem,
        ]);
      }
    } catch (sendError) {
      setItems((current) => current.filter((item) => item.id !== councilId));
      setError(sendError instanceof Error ? sendError.message : "Failed to send message.");
    } finally {
      activeCouncilIdRef.current = null;
      setAwaitingResponse(false);
      void refreshSourceCount(apiKey);
    }
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
      <header className="dom-header layout-thread">
        <div>
          <p className="overline">domAIn</p>
          <h1 className="dom-header__title">Chat</h1>
        </div>
        <p className="caption">{connected ? "Connected" : "Connecting"}</p>
      </header>

      <section className="dom-chat layout-thread" aria-live="polite">
        {!historyLoaded ? <p className="caption">Loading chat history</p> : <ChatThread items={items} />}
      </section>

      {error ? <p className="dom-error layout-thread caption">{error}</p> : null}

      <footer className="dom-footer layout-thread">
        <Composer
          disabled={awaitingResponse || !connected}
          readySourceCount={readySourceCount}
          onSend={(content) => {
            void handleSend(content);
          }}
        />
      </footer>
    </main>
  );
}
