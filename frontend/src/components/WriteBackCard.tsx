import { useState } from "react";
import {
  confirmWriteBackProposal,
  proposeWriteBack,
  refineWriteBackProposal,
} from "../lib/api";
import { isEmptyWriteBackPlan, planActionLines } from "../lib/writeBackPlan";
import type { WriteBackProposalOut } from "../types/chat";

interface WriteBackCardProps {
  messageId: string;
  proposal: WriteBackProposalOut | null;
  apiKey: string;
  onProposalUpdate: (proposal: WriteBackProposalOut) => void;
}

function SuccessCheckIcon() {
  return (
    <svg className="dom-write-back-card__check" viewBox="0 0 16 16" aria-hidden="true">
      <path
        d="M3.5 8.5 6.5 11.5 12.5 4.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function WriteBackCard({
  messageId,
  proposal,
  apiKey,
  onProposalUpdate,
}: WriteBackCardProps) {
  const [feedback, setFeedback] = useState("");
  const [executing, setExecuting] = useState(false);
  const [proposing, setProposing] = useState(false);
  const [refining, setRefining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePropose = async () => {
    setProposing(true);
    setError(null);
    try {
      const created = await proposeWriteBack(apiKey, messageId);
      onProposalUpdate(created);
    } catch (proposeError) {
      setError(
        proposeError instanceof Error ? proposeError.message : "Failed to propose write-back.",
      );
    } finally {
      setProposing(false);
    }
  };

  const handleRefine = async () => {
    if (!proposal || !feedback.trim()) {
      return;
    }
    setRefining(true);
    setError(null);
    try {
      const refined = await refineWriteBackProposal(apiKey, proposal.id, feedback.trim());
      onProposalUpdate(refined);
      setFeedback("");
    } catch (refineError) {
      setError(
        refineError instanceof Error ? refineError.message : "Failed to refine write-back plan.",
      );
    } finally {
      setRefining(false);
    }
  };

  const handleConfirm = async () => {
    if (!proposal) {
      return;
    }
    setExecuting(true);
    setError(null);
    try {
      const confirmed = await confirmWriteBackProposal(apiKey, proposal.id);
      onProposalUpdate(confirmed);
    } catch (confirmError) {
      setError(
        confirmError instanceof Error ? confirmError.message : "Failed to confirm write-back.",
      );
    } finally {
      setExecuting(false);
    }
  };

  if (!proposal) {
    return (
      <div className="dom-write-back-card">
        {error ? <p className="dom-write-back-card__error caption">{error}</p> : null}
        <button
          type="button"
          className="dom-btn dom-btn--secondary dom-btn--sm"
          disabled={proposing}
          onClick={() => {
            void handlePropose();
          }}
        >
          Propose write-back
        </button>
      </div>
    );
  }

  if (proposal.status === "executed") {
    return (
      <div className="dom-write-back-card dom-write-back-card--executed">
        <ul className="dom-write-back-card__list">
          {proposal.execution_results.map((result) => (
            <li key={`${result.kind}-${result.url}`} className="dom-write-back-card__result">
              <SuccessCheckIcon />
              <a href={result.url} target="_blank" rel="noreferrer">
                {result.label}
              </a>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  const emptyPlan = isEmptyWriteBackPlan(proposal.plan);
  const planLines = planActionLines(proposal.plan);

  return (
    <div className="dom-write-back-card">
      {error ? <p className="dom-write-back-card__error caption">{error}</p> : null}

      {emptyPlan ? (
        <p className="dom-write-back-card__empty caption">No follow-up action needed.</p>
      ) : (
        <ul className="dom-write-back-card__list">
          {planLines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}

      <label className="dom-write-back-card__field">
        <span className="caption">Feedback</span>
        <textarea
          className="dom-write-back-card__input"
          rows={2}
          value={feedback}
          disabled={executing}
          placeholder="Optional refinement notes"
          onChange={(event) => setFeedback(event.target.value)}
        />
      </label>

      <div className="dom-write-back-card__actions">
        <button
          type="button"
          className="dom-btn dom-btn--secondary dom-btn--sm"
          disabled={executing || refining || !feedback.trim()}
          onClick={() => {
            void handleRefine();
          }}
        >
          Refine
        </button>
        {!emptyPlan ? (
          error ? (
            <button
              type="button"
              className="dom-btn dom-btn--secondary dom-btn--sm"
              disabled={executing}
              onClick={() => {
                void handleConfirm();
              }}
            >
              Retry
            </button>
          ) : (
            <button
              type="button"
              className="dom-btn dom-btn--primary dom-btn--sm"
              disabled={executing}
              onClick={() => {
                void handleConfirm();
              }}
            >
              Confirm
            </button>
          )
        ) : null}
      </div>
    </div>
  );
}
