import { describe, expect, it } from "vitest";
import { applyStatusUpdate, createInitialPendingState } from "./councilState";
import { PERSONA_DISPLAY } from "./personaMap";
import { personaStatusLabel, supervisorStatusLabel } from "./statusLabels";
import { isChatResponse, isChatStatusUpdate } from "../types/chat";

describe("persona mapping", () => {
  it("maps backend persona ids to design-system marks", () => {
    expect(PERSONA_DISPLAY.ux.mark).toBe("ux");
    expect(PERSONA_DISPLAY.dev_experience.mark).toBe("dx");
    expect(PERSONA_DISPLAY.business.mark).toBe("bp");
  });
});

describe("status labels", () => {
  it("formats supervisor and persona statuses as readable text", () => {
    expect(supervisorStatusLabel("waiting_on_council")).toBe("Waiting on council");
    expect(personaStatusLabel("researching")).toBe("Researching");
  });
});

describe("frame guards", () => {
  it("distinguishes status updates from final responses", () => {
    expect(
      isChatStatusUpdate({
        session_id: "00000000-0000-4000-8000-000000000001",
        scope: "supervisor",
        persona: null,
        status: "alerting_council",
      }),
    ).toBe(true);
    expect(
      isChatResponse({
        session_id: "00000000-0000-4000-8000-000000000001",
        content: "Hello",
        classified_intent: "greeting",
        response_kind: "direct_answer",
        citations: [],
        council_decision: null,
      }),
    ).toBe(true);
  });
});

describe("pending council state", () => {
  it("updates supervisor and persona seats independently", () => {
    const initial = createInitialPendingState();
    const waiting = applyStatusUpdate(initial, {
      session_id: "00000000-0000-4000-8000-000000000001",
      scope: "supervisor",
      persona: null,
      status: "waiting_on_council",
    });
    expect(waiting.supervisorStatus).toBe("waiting_on_council");

    const uxReady = applyStatusUpdate(waiting, {
      session_id: "00000000-0000-4000-8000-000000000001",
      scope: "persona",
      persona: "ux",
      status: "recommendation_ready",
    });
    expect(uxReady.seats.ux.ready).toBe(true);
    expect(uxReady.seats.dev_experience.ready).toBe(false);
  });
});
