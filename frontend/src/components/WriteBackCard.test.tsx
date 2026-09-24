import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  confirmWriteBackProposal,
  proposeWriteBack,
  refineWriteBackProposal,
} from "../lib/api";
import type { WriteBackProposalOut } from "../types/chat";
import { WriteBackCard } from "./WriteBackCard";

vi.mock("../lib/api", () => ({
  proposeWriteBack: vi.fn(),
  refineWriteBackProposal: vi.fn(),
  confirmWriteBackProposal: vi.fn(),
}));

const mockedProposeWriteBack = vi.mocked(proposeWriteBack);
const mockedRefineWriteBackProposal = vi.mocked(refineWriteBackProposal);
const mockedConfirmWriteBackProposal = vi.mocked(confirmWriteBackProposal);

function buildProposal(overrides: Partial<WriteBackProposalOut> = {}): WriteBackProposalOut {
  return {
    id: "proposal-1",
    chat_message_id: "message-1",
    user_id: "user-1",
    project_id: null,
    plan: {
      needs_doc_update: true,
      doc_target: "new",
      existing_doc_path: null,
      new_doc_slug: "council-scope",
      needs_roadmap_item: false,
    },
    feedback_history: [],
    status: "proposed",
    execution_results: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    executed_at: null,
    ...overrides,
  };
}

function WriteBackCardHarness({
  initialProposal = null,
}: {
  initialProposal?: WriteBackProposalOut | null;
}) {
  const [proposal, setProposal] = useState<WriteBackProposalOut | null>(initialProposal);

  return (
    <WriteBackCard
      messageId="message-1"
      apiKey="test-key"
      proposal={proposal}
      onProposalUpdate={setProposal}
    />
  );
}

describe("WriteBackCard", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("proposes write-back from the untriggered state and renders the returned plan", async () => {
    const user = userEvent.setup();
    const created = buildProposal();

    mockedProposeWriteBack.mockResolvedValue(created);

    render(<WriteBackCardHarness />);

    await user.click(screen.getByRole("button", { name: "Propose write-back" }));

    await waitFor(() => {
      expect(mockedProposeWriteBack).toHaveBeenCalledWith("test-key", "message-1");
    });
    expect(screen.getByText("Create new doc: council-scope")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Propose write-back" })).not.toBeInTheDocument();
  });

  it("refines the plan in place with typed feedback", async () => {
    const user = userEvent.setup();
    const initial = buildProposal();
    const refined = buildProposal({
      plan: {
        needs_doc_update: true,
        doc_target: "new",
        existing_doc_path: null,
        new_doc_slug: "council-scope-refined",
        needs_roadmap_item: true,
      },
    });

    mockedRefineWriteBackProposal.mockResolvedValue(refined);

    render(<WriteBackCardHarness initialProposal={initial} />);

    await user.type(screen.getByPlaceholderText("Optional refinement notes"), "Add roadmap item");
    await user.click(screen.getByRole("button", { name: "Refine" }));

    await waitFor(() => {
      expect(mockedRefineWriteBackProposal).toHaveBeenCalledWith(
        "test-key",
        "proposal-1",
        "Add roadmap item",
      );
    });
    expect(screen.getByText("Create new doc: council-scope-refined")).toBeInTheDocument();
    expect(screen.getByText("Create Linear roadmap item")).toBeInTheDocument();
    expect(screen.queryByText("Create new doc: council-scope")).not.toBeInTheDocument();
  });

  it("confirms write-back and renders executed result links", async () => {
    const user = userEvent.setup();
    const initial = buildProposal();
    const executed = buildProposal({
      status: "executed",
      executed_at: "2026-01-02T00:00:00Z",
      execution_results: [
        {
          kind: "github_pr",
          label: "Add council decision doc (council-scope)",
          url: "https://github.com/owner/repo/pull/1",
        },
      ],
    });

    mockedConfirmWriteBackProposal.mockResolvedValue(executed);

    render(<WriteBackCardHarness initialProposal={initial} />);

    await user.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() => {
      expect(mockedConfirmWriteBackProposal).toHaveBeenCalledWith("test-key", "proposal-1");
    });
    expect(
      screen.getByRole("link", { name: "Add council decision doc (council-scope)" }),
    ).toHaveAttribute("href", "https://github.com/owner/repo/pull/1");
    expect(screen.queryByText("Create new doc: council-scope")).not.toBeInTheDocument();
  });

  it("shows a retryable error without hiding the plan or feedback field", async () => {
    const user = userEvent.setup();
    const initial = buildProposal();

    mockedConfirmWriteBackProposal.mockRejectedValue(new Error("Linear API unavailable"));

    render(<WriteBackCardHarness initialProposal={initial} />);

    await user.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() => {
      expect(screen.getByText("Linear API unavailable")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm" })).not.toBeInTheDocument();
    expect(screen.getByText("Create new doc: council-scope")).toBeInTheDocument();

    const feedback = screen.getByPlaceholderText("Optional refinement notes");
    expect(feedback).toBeEnabled();
    await user.type(feedback, "Try again with smaller scope");
    expect(feedback).toHaveValue("Try again with smaller scope");
  });

  it("renders an empty plan without confirm or retry actions", () => {
    const emptyPlan = buildProposal({
      plan: {
        needs_doc_update: false,
        doc_target: null,
        existing_doc_path: null,
        new_doc_slug: null,
        needs_roadmap_item: false,
      },
    });

    render(<WriteBackCardHarness initialProposal={emptyPlan} />);

    expect(screen.getByText("No follow-up action needed.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });
});
