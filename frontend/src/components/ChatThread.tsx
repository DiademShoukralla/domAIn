import { personaVoiceFor } from "../lib/personaMap";
import type { ThreadItem } from "../types/chat";
import { ChatMessage } from "./ChatMessage";

interface ChatThreadProps {
  items: ThreadItem[];
}

function CouncilThreadBlock({ item }: { item: Extract<ThreadItem, { kind: "council" }> }) {
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
      <ChatMessage voice="chair" content={item.content} councilDecision={item.councilDecision} />
    </div>
  );
}

export function ChatThread({ items }: ChatThreadProps) {
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
        return <CouncilThreadBlock key={item.id} item={item} />;
      })}
    </div>
  );
}
