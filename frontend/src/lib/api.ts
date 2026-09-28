import type {
  ChatHistoryResponse,
  ChatMessageOut,
  ThreadItem,
  WriteBackProposalOut,
} from "../types/chat";
import type { KnowledgeSource, KnowledgeSourceListResponse } from "../types/sources";
import { humanizeApiError } from "./authErrors";

function apiHeaders(extra: HeadersInit = {}): HeadersInit {
  return {
    Accept: "application/json",
    ...extra,
  };
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(humanizeApiError(response.status, detail));
  }
  return (await response.json()) as T;
}

const fetchOptions: RequestInit = {
  credentials: "include",
};

export async function fetchChatHistory(sessionId: string): Promise<ChatHistoryResponse> {
  const response = await fetch(`/chat/sessions/${sessionId}/messages`, {
    ...fetchOptions,
    headers: apiHeaders(),
  });
  return parseJson<ChatHistoryResponse>(response);
}

export async function fetchSourceCount(): Promise<number> {
  const payload = await fetchSources();
  return payload.sources.filter((source) => source.status === "ready").length;
}

export async function fetchSources(): Promise<KnowledgeSourceListResponse> {
  const response = await fetch("/sources", {
    ...fetchOptions,
    headers: apiHeaders(),
  });
  return parseJson<KnowledgeSourceListResponse>(response);
}

export async function deleteSource(sourceId: string): Promise<void> {
  const response = await fetch(`/sources/${sourceId}`, {
    ...fetchOptions,
    method: "DELETE",
    headers: apiHeaders(),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(humanizeApiError(response.status, detail));
  }
}

export async function refreshSource(sourceId: string): Promise<KnowledgeSource> {
  const response = await fetch(`/sources/${sourceId}/refresh`, {
    ...fetchOptions,
    method: "POST",
    headers: apiHeaders(),
  });
  return parseJson<KnowledgeSource>(response);
}

export function historyToThreadItems(messages: ChatMessageOut[]): ThreadItem[] {
  return messages.flatMap((message) => threadItemsFromHistoryMessage(message));
}

export async function proposeWriteBack(messageId: string): Promise<WriteBackProposalOut> {
  const response = await fetch(`/chat/messages/${messageId}/write-back`, {
    ...fetchOptions,
    method: "POST",
    headers: apiHeaders(),
  });
  return parseJson<WriteBackProposalOut>(response);
}

export async function refineWriteBackProposal(
  proposalId: string,
  feedback: string,
): Promise<WriteBackProposalOut> {
  const response = await fetch(`/write-back-proposals/${proposalId}`, {
    ...fetchOptions,
    method: "PATCH",
    headers: apiHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({ feedback }),
  });
  return parseJson<WriteBackProposalOut>(response);
}

export async function confirmWriteBackProposal(proposalId: string): Promise<WriteBackProposalOut> {
  const response = await fetch(`/write-back-proposals/${proposalId}/confirm`, {
    ...fetchOptions,
    method: "POST",
    headers: apiHeaders(),
  });
  return parseJson<WriteBackProposalOut>(response);
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
        writeBackProposal: message.write_back_proposal,
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
