import type { FormEvent, KeyboardEvent } from "react"
import { Loader2, Send } from "lucide-react"

import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { MessageBubble } from "@/features/chat/components/MessageBubble"
import type { ChatMessage } from "@/lib/chat-stream"

type ConversationPanelProps = {
  messages: ChatMessage[]
  input: string
  error: string
  isSending: boolean
  canSend: boolean
  setInput: (input: string) => void
  sendMessage: () => Promise<void>
}

export function ConversationPanel({
  messages,
  input,
  error,
  isSending,
  canSend,
  setInput,
  sendMessage,
}: ConversationPanelProps) {
  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    void sendMessage()
  }

  function handleInputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      void sendMessage()
    }
  }

  return (
    <div className="flex min-h-[620px] flex-col">
      <ScrollArea className="min-h-0 flex-1 rounded-md border">
        <div className="space-y-4 p-4">
          {messages.map((message, index) => (
            <MessageBubble key={`${message.role}-${index}`} message={message} />
          ))}
          {isSending && messages.at(-1)?.content === "" ? <StreamingIndicator /> : null}
        </div>
      </ScrollArea>

      {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}

      <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
        <Textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleInputKeyDown}
          placeholder="输入消息，Enter 发送，Shift + Enter 换行"
          disabled={isSending}
        />
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">History is kept in the browser and sent every turn.</p>
          <Button type="submit" disabled={!canSend}>
            {isSending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            Send
          </Button>
        </div>
      </form>
    </div>
  )
}

function StreamingIndicator() {
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      streaming...
    </div>
  )
}
