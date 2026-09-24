import { personaVoiceFor } from "../lib/personaMap";
import type { ThreadItem, WriteBackProposalOut } from "../types/chat";
import { ChatMessage } from "./ChatMessage";

interface ChatThreadProps {
  items: ThreadItem[];
  apiKey: string;
  onWriteBackProposalUpdate: (messageId: string, proposal: WriteBackProposalOut) => void;
}

function CouncilThreadBlock({
  item,
  apiKey,
  onWriteBackProposalUpdate,
}: {
  item: Extract<ThreadItem, { kind: "council" }>;
  apiKey: string;
  onWriteBackProposalUpdate: (messageId: string, proposal: WriteBackProposalOut) => void;
}) {
  if (item.phase === "pending") {
    return <ChatMessage voice="pending" pending={item.pending} />;
  }

  return (
    <div className="dom-council-result">
      {item.councilDecision.persona_opinions.map((opinion) => {
        const voice = personaVoiceFor(opinion.persona);
        if (!voice) {
          return null;
        }
        return (
          <ChatMessage
            key={`${item.id}-${opinion.persona}`}
            voice={voice}
            opinion={opinion}
          />
        );
      })}
      <ChatMessage
        voice="chair"
        content={item.content}
        councilDecision={item.councilDecision}
        messageId={item.id}
        apiKey={apiKey}
        writeBackProposal={item.writeBackProposal}
        onWriteBackProposalUpdate={(proposal) => onWriteBackProposalUpdate(item.id, proposal)}
      />
    </div>
  );
}

export function ChatThread({ items, apiKey, onWriteBackProposalUpdate }: ChatThreadProps) {
  return (
    <div className="dom-chat-thread">
      {items.map((item) => {
        if (item.kind === "user") {
          return <ChatMessage key={item.id} voice="you" content={item.content} />;
        }
        if (item.kind === "direct") {
          return (
            <ChatMessage
              key={item.id}
              voice="direct"
              content={item.content}
              citations={item.citations}
            />
          );
        }
        if (item.kind === "stub") {
          return <ChatMessage key={item.id} voice="direct" content={item.content} />;
        }
        return (
          <CouncilThreadBlock
            key={item.id}
            item={item}
            apiKey={apiKey}
            onWriteBackProposalUpdate={onWriteBackProposalUpdate}
          />
        );
      })}
    </div>
  );
}
