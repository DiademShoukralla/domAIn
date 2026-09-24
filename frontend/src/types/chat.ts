export type Verdict = "approve" | "request_changes" | "comment";

export interface Citation {
  document_id: string;
  chunk_index: number;
  knowledge_source_id: string;
  excerpt: string;
}

export interface PersonaOpinion {
  persona: string;
  verdict: Verdict;
  reasoning: string;
  citations: Citation[];
}

export interface CouncilDecision {
  persona_opinions: PersonaOpinion[];
  overall_verdict: Verdict;
  synthesis: string;
}

export type ChatIntent =
  | "greeting"
  | "simple_retrieval"
  | "strategic_session"
  | "linear_read"
  | "linear_write";

export type ResponseKind =
  | "direct_answer"
  | "council_result"
  | "stub_not_implemented";

export type WriteBackProposalStatus = "proposed" | "confirmed" | "executed";

export interface WriteBackPlan {
  needs_doc_update: boolean;
  doc_target: "existing" | "new" | null;
  existing_doc_path: string | null;
  new_doc_slug: string | null;
  needs_roadmap_item: boolean;
}

export interface WriteBackFeedbackEntry {
  feedback: string;
  created_at: string;
}

export interface WriteBackProposalOut {
  id: string;
  chat_message_id: string;
  user_id: string;
  project_id: string | null;
  plan: WriteBackPlan;
  feedback_history: WriteBackFeedbackEntry[];
  status: WriteBackProposalStatus;
  created_at: string;
  updated_at: string;
  executed_at: string | null;
}

export interface ChatMessageIn {
  session_id: string;
  content: string;
}

export interface ChatResponse {
  session_id: string;
  content: string;
  classified_intent: ChatIntent;
  response_kind: ResponseKind;
  citations: Citation[];
  council_decision: CouncilDecision | null;
}

export interface ChatStatusUpdate {
  session_id: string;
  scope: "supervisor" | "persona";
  persona: string | null;
  status: string;
}

export interface ChatMessageOut {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  classified_intent: ChatIntent | null;
  response_kind: ResponseKind | null;
  citations: Citation[];
  council_decision: CouncilDecision | null;
  write_back_proposal: WriteBackProposalOut | null;
  created_at: string;
}

export interface ChatHistoryResponse {
  session_id: string;
  messages: ChatMessageOut[];
}

export interface KnowledgeSource {
  id: string;
  status: "pending" | "indexing" | "ready" | "error";
}

export interface KnowledgeSourceListResponse {
  sources: KnowledgeSource[];
}

export type ChatMessageVoice =
  | "you"
  | "direct"
  | "ux"
  | "dx"
  | "biz"
  | "chair"
  | "pending";

export type PersonaBackendId = "ux" | "dev_experience" | "business";

export interface PersonaSeatState {
  personaId: PersonaBackendId;
  status: string | null;
  ready: boolean;
}

export interface CouncilPendingState {
  supervisorStatus: string;
  seats: Record<PersonaBackendId, PersonaSeatState>;
}

export type ThreadItem =
  | {
      id: string;
      kind: "user";
      content: string;
    }
  | {
      id: string;
      kind: "direct";
      content: string;
      citations: Citation[];
    }
  | {
      id: string;
      kind: "stub";
      content: string;
    }
  | {
      id: string;
      kind: "council";
      phase: "pending";
      pending: CouncilPendingState;
    }
  | {
      id: string;
      kind: "council";
      phase: "complete";
      content: string;
      councilDecision: CouncilDecision;
    };

export type IncomingFrame = ChatResponse | ChatStatusUpdate;

export function isChatResponse(frame: IncomingFrame): frame is ChatResponse {
  return "response_kind" in frame;
}

export function isChatStatusUpdate(frame: IncomingFrame): frame is ChatStatusUpdate {
  return "scope" in frame;
}
