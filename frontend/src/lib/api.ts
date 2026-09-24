import type {
  ChatHistoryResponse,
  ChatMessageOut,
  ThreadItem,
} from "../types/chat";
import type { KnowledgeSource, KnowledgeSourceListResponse } from "../types/sources";

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
  const payload = await fetchSources(apiKey);
  return payload.sources.filter((source) => source.status === "ready").length;
}

export async function fetchSources(apiKey: string): Promise<KnowledgeSourceListResponse> {
  const response = await fetch("/sources", {
    headers: apiHeaders(apiKey),
  });
  return parseJson<KnowledgeSourceListResponse>(response);
}

export async function deleteSource(apiKey: string, sourceId: string): Promise<void> {
  const response = await fetch(`/sources/${sourceId}`, {
    method: "DELETE",
    headers: apiHeaders(apiKey),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
}

export async function refreshSource(apiKey: string, sourceId: string): Promise<KnowledgeSource> {
  const response = await fetch(`/sources/${sourceId}/refresh`, {
    method: "POST",
    headers: apiHeaders(apiKey),
  });
  return parseJson<KnowledgeSource>(response);
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
