import type { ChatMessage } from "@/lib/chat-stream"
import { cn } from "@/lib/utils"

type MessageBubbleProps = {
  message: ChatMessage
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user"

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[min(720px,90%)] rounded-md border px-3 py-2 text-sm leading-6 shadow-sm",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
        )}
      >
        <div className="mb-1 text-[11px] font-medium uppercase tracking-normal opacity-70">
          {isUser ? "user" : "assistant"}
        </div>
        <div className="whitespace-pre-wrap break-words">{message.content || "..."}</div>
      </div>
    </div>
  )
}
