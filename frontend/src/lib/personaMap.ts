import type { PersonaBackendId } from "../types/chat";

export interface PersonaDisplay {
  mark: string;
  name: string;
  markClass: "ux" | "dx" | "biz";
  voice: "ux" | "dx" | "biz";
}

export const PERSONA_IDS: readonly PersonaBackendId[] = [
  "ux",
  "dev_experience",
  "business",
] as const;

export const PERSONA_DISPLAY: Record<PersonaBackendId, PersonaDisplay> = {
  ux: {
    mark: "ux",
    name: "UX",
    markClass: "ux",
    voice: "ux",
  },
  dev_experience: {
    mark: "dx",
    name: "Dev experience",
    markClass: "dx",
    voice: "dx",
  },
  business: {
    mark: "bp",
    name: "Business",
    markClass: "biz",
    voice: "biz",
  },
};

export function personaDisplayFor(personaId: string): PersonaDisplay | null {
  if (personaId in PERSONA_DISPLAY) {
    return PERSONA_DISPLAY[personaId as PersonaBackendId];
  }
  return null;
}

export function personaVoiceFor(personaId: string): "ux" | "dx" | "biz" | null {
  return personaDisplayFor(personaId)?.voice ?? null;
}
