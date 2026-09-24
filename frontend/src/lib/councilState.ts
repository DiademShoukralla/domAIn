import { PERSONA_IDS } from "./personaMap";
import type {
  ChatResponse,
  ChatStatusUpdate,
  CouncilPendingState,
  PersonaBackendId,
  PersonaSeatState,
} from "../types/chat";

export const OPTIMISTIC_STATUS = "Understanding the message";

export function createInitialPendingState(): CouncilPendingState {
  const seats = Object.fromEntries(
    PERSONA_IDS.map((personaId) => [
      personaId,
      {
        personaId,
        status: null,
        ready: false,
      } satisfies PersonaSeatState,
    ]),
  ) as Record<PersonaBackendId, PersonaSeatState>;

  return {
    supervisorStatus: OPTIMISTIC_STATUS,
    seats,
  };
}

export function applyStatusUpdate(
  pending: CouncilPendingState,
  update: ChatStatusUpdate,
): CouncilPendingState {
  if (update.scope === "supervisor") {
    return {
      ...pending,
      supervisorStatus: update.status,
    };
  }

  if (!update.persona || !(update.persona in pending.seats)) {
    return pending;
  }

  const personaId = update.persona as PersonaBackendId;
  const current = pending.seats[personaId];
  return {
    ...pending,
    seats: {
      ...pending.seats,
      [personaId]: {
        ...current,
        status: update.status,
        ready: update.status === "recommendation_ready" || current.ready,
      },
    },
  };
}

export function councilItemFromResponse(response: ChatResponse) {
  if (response.response_kind !== "council_result" || !response.council_decision) {
    throw new Error("Expected council_result response");
  }

  return {
    id: response.id,
    kind: "council" as const,
    phase: "complete" as const,
    content: response.content,
    councilDecision: response.council_decision,
    writeBackProposal: null,
  };
}

export function directItemFromResponse(response: ChatResponse) {
  if (response.response_kind === "stub_not_implemented") {
    return {
      id: response.id,
      kind: "stub" as const,
      content: response.content,
    };
  }

  return {
    id: response.id,
    kind: "direct" as const,
    content: response.content,
    citations: response.citations,
  };
}
