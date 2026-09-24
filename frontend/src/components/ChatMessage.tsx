import { useEffect, useRef } from "react";
import { PERSONA_DISPLAY, PERSONA_IDS } from "../lib/personaMap";
import { personaStatusLabel, supervisorStatusLabel } from "../lib/statusLabels";
import type {
  ChatMessageVoice,
  CouncilDecision,
  CouncilPendingState,
  PersonaOpinion,
} from "../types/chat";
import { CodeCitation } from "./CodeCitation";
import { VerdictBadge } from "./VerdictBadge";

interface ChatMessageProps {
  voice: ChatMessageVoice;
  content?: string;
  citations?: Array<{ document_id: string; chunk_index: number; knowledge_source_id: string; excerpt: string }>;
  opinion?: PersonaOpinion;
  councilDecision?: CouncilDecision;
  pending?: CouncilPendingState;
}

function PersonaHeader({
  voice,
  verdict,
}: {
  voice: "ux" | "dx" | "biz";
  verdict?: string;
}) {
  const display =
    voice === "ux"
      ? PERSONA_DISPLAY.ux
      : voice === "dx"
        ? PERSONA_DISPLAY.dev_experience
        : PERSONA_DISPLAY.business;

  return (
    <header className="dom-persona-message__header">
      <span
        className={`dom-persona-message__mark dom-persona-message__mark--${display.markClass} mono-label`}
      >
        {display.mark}
      </span>
      <span className={`dom-persona-message__name dom-persona-message__name--${display.markClass}`}>
        {display.name}
      </span>
      {verdict ? <VerdictBadge verdict={verdict} /> : null}
    </header>
  );
}

function PendingCouncilMessage({ pending }: { pending: CouncilPendingState }) {
  return (
    <article className="dom-chair-block dom-chair-block--pending" aria-live="polite">
      <header className="dom-chair-block__header">
        <span className="dom-chair-block__label">Council</span>
        <span className="dom-council-pulse">
          <span className="dom-council-pulse__dot" aria-hidden="true" />
          <span className="caption">{supervisorStatusLabel(pending.supervisorStatus)}</span>
        </span>
      </header>
      <div className="dom-council-seats" aria-label="Council seat status">
        {PERSONA_IDS.map((personaId) => {
          const display = PERSONA_DISPLAY[personaId];
          const seat = pending.seats[personaId];
          const label = seat.ready
            ? "Recommendation ready"
            : personaStatusLabel(seat.status);

          return (
            <div
              key={personaId}
              className={`dom-council-seat${seat.ready ? " dom-council-seat--ready" : ""}`}
            >
              <span
                className={`dom-persona-message__mark dom-persona-message__mark--${display.markClass} mono-label`}
              >
                {display.mark}
              </span>
              <span className="caption">{label}</span>
            </div>
          );
        })}
      </div>
    </article>
  );
}

export function ChatMessage({
  voice,
  content = "",
  citations = [],
  opinion,
  councilDecision,
  pending,
}: ChatMessageProps) {
  if (voice === "you") {
    return (
      <article className="dom-user-message">
        <div className="body">{content}</div>
      </article>
    );
  }

  if (voice === "direct") {
    return (
      <article className="dom-retrieval-message">
        <div className="body">{content}</div>
        {citations.map((citation) => (
          <CodeCitation key={`${citation.document_id}-${citation.chunk_index}`} citation={citation} />
        ))}
      </article>
    );
  }

  if (voice === "pending" && pending) {
    return <PendingCouncilMessage pending={pending} />;
  }

  if ((voice === "ux" || voice === "dx" || voice === "biz") && opinion) {
    return (
      <article className="dom-persona-message">
        <PersonaHeader voice={voice} verdict={opinion.verdict} />
        <div className="body">{opinion.reasoning}</div>
        {opinion.citations.map((citation) => (
          <CodeCitation key={`${citation.document_id}-${citation.chunk_index}`} citation={citation} />
        ))}
      </article>
    );
  }

  if (voice === "chair" && councilDecision) {
    return (
      <article className="dom-chair-block">
        <header className="dom-chair-block__header">
          <span className="dom-chair-block__label">Recommendation</span>
          <VerdictBadge verdict={councilDecision.overall_verdict} />
        </header>
        <div className="body-lg">{councilDecision.synthesis || content}</div>
      </article>
    );
  }

  return (
    <article className="dom-retrieval-message">
      <div className="body">{content}</div>
    </article>
  );
}

interface ComposerProps {
  disabled: boolean;
  readySourceCount: number | null;
  onSend: (content: string) => void;
}

export function Composer({ disabled, readySourceCount, onSend }: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
    textarea.style.height = "auto";
    const maxHeight = 24 * 4 + 16;
    textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
  });

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
    const value = textarea.value.trim();
    if (!value || disabled) {
      return;
    }
    onSend(value);
    textarea.value = "";
    textarea.style.height = "auto";
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  const sourceHint =
    readySourceCount === null
      ? "Loading source count"
      : readySourceCount === 1
        ? "1 source indexed"
        : `${readySourceCount} sources indexed`;

  return (
    <form className="dom-composer" role="form" aria-label="Send a message" onSubmit={handleSubmit}>
      <div className="dom-composer__stack">
        <p className="dom-composer__hint caption">{sourceHint}</p>
        <textarea
          ref={textareaRef}
          className="dom-composer__input"
          rows={1}
          placeholder="Ask a question or submit a proposal for review"
          aria-label="Message"
          disabled={disabled}
          onKeyDown={handleKeyDown}
          onInput={() => {
            const textarea = textareaRef.current;
            if (!textarea) {
              return;
            }
            textarea.style.height = "auto";
            const maxHeight = 24 * 4 + 16;
            textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
          }}
        />
      </div>
      <button type="submit" className="dom-composer__submit" aria-label="Send" disabled={disabled}>
        Send
      </button>
    </form>
  );
}
