import type {
  ChatHistoryResponse,
  ChatMessageOut,
  KnowledgeSourceListResponse,
  ThreadItem,
} from "../types/chat";

function apiHeaders(apiKey: string): HeadersInit {
  return {
    "X-API-Key": apiKey,
    Accept: "application/json",
  };
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function fetchChatHistory(
  sessionId: string,
  apiKey: string,
): Promise<ChatHistoryResponse> {
  const response = await fetch(`/chat/sessions/${sessionId}/messages`, {
    headers: apiHeaders(apiKey),
  });
  return parseJson<ChatHistoryResponse>(response);
}

export async function fetchSourceCount(apiKey: string): Promise<number> {
  const response = await fetch("/sources", {
    headers: apiHeaders(apiKey),
  });
  const payload = await parseJson<KnowledgeSourceListResponse>(response);
  return payload.sources.filter((source) => source.status === "ready").length;
}

export function historyToThreadItems(messages: ChatMessageOut[]): ThreadItem[] {
  return messages.flatMap((message) => threadItemsFromHistoryMessage(message));
}

export function threadItemsFromHistoryMessage(message: ChatMessageOut): ThreadItem[] {
  if (message.role === "user") {
    return [
      {
        id: message.id,
        kind: "user" as const,
        content: message.content,
      },
    ];
  }

  if (message.response_kind === "council_result" && message.council_decision) {
    return [
      {
        id: message.id,
        kind: "council" as const,
        phase: "complete" as const,
        content: message.content,
        councilDecision: message.council_decision,
      },
    ];
  }

  if (message.response_kind === "stub_not_implemented") {
    return [
      {
        id: message.id,
        kind: "stub" as const,
        content: message.content,
      },
    ];
  }

  return [
    {
      id: message.id,
      kind: "direct" as const,
      content: message.content,
      citations: message.citations,
    },
  ];
}
