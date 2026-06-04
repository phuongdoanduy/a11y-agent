import { useEffect, useRef } from "react";
import type { Message } from "../App";

interface Props {
  messages: Message[];
  isStreaming: boolean;
}

export function ChatMessagesView({ messages, isStreaming }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4">
      <div className="mx-auto max-w-3xl space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-brand/20 text-brand-light"
                  : "bg-zinc-800/80 text-zinc-200"
              }`}
            >
              {msg.agent && (
                <div className="mb-1 text-xs font-medium text-zinc-500">
                  {msg.agent.replace(/_/g, " ")}
                </div>
              )}
              <div className="whitespace-pre-wrap">
                {msg.content || (isStreaming && msg.role === "agent" ? <ThinkingDots /> : null)}
              </div>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

function ThinkingDots() {
  return (
    <span className="inline-flex gap-1">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:0ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:150ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:300ms]" />
    </span>
  );
}
