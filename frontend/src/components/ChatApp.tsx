import { useCallback, useEffect, useRef, useState } from "react";
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
import { getOrCreateSessionId } from "../lib/session";
import { appPath } from "../lib/routing";
import type { IncomingFrame, ThreadItem } from "../types/chat";
import { isChatResponse, isChatStatusUpdate } from "../types/chat";
import { useChatWebSocket } from "../hooks/useChatWebSocket";
import { ChatThread } from "./ChatThread";
import { Composer } from "./ChatMessage";

export function ChatApp({ apiKey }: { apiKey: string }) {
  const [sessionId] = useState(getOrCreateSessionId);
  const [items, setItems] = useState<ThreadItem[]>([]);
  const [readySourceCount, setReadySourceCount] = useState<number | null>(null);
  const [awaitingResponse, setAwaitingResponse] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  const activeCouncilIdRef = useRef<string | null>(null);

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

  const handleSend = async (content: string) => {
    if (awaitingResponse) {
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

  return (
    <>
      <header className="dom-header layout-thread">
        <div>
          <p className="overline">domAIn</p>
          <h1 className="dom-header__title">Chat</h1>
        </div>
        <div className="dom-header__aside">
          <nav className="dom-nav" aria-label="App sections">
            <a className="dom-nav__link dom-nav__link--active" href={appPath("chat")} aria-current="page">
              Chat
            </a>
            <a className="dom-nav__link" href={appPath("connections")}>
              Connections
            </a>
          </nav>
          <p className="caption">{connected ? "Connected" : "Connecting"}</p>
        </div>
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
    </>
  );
}
