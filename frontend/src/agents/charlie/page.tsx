import { useCallback, useMemo, useState } from "react"
import { Loader2, Send } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

import { streamCharlieChat } from "./api"
import type { CharlieMessage } from "./types"

const initialMessages: CharlieMessage[] = [{ role: "assistant", content: "Charlie ready." }]

export function CharliePage() {
  // 当前页面很小,hook 和小展示函数留在本文件;超过单人可读范围时再拆。
  const chat = useCharlieChat()

  return (
    <section className="flex min-h-[720px] flex-col py-5">
      <div className="mb-4">
        <h2 className="text-lg font-semibold">Charlie</h2>
        <p className="text-sm text-muted-foreground">Owned by the Charlie developer.</p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto rounded-md border p-4">
        <div className="space-y-4">
          {chat.messages.map((message, index) => (
            <MessageBubble key={`${message.role}-${index}`} message={message} />
          ))}
          {chat.isSending && chat.messages.at(-1)?.content === "" ? (
            <div className="text-sm text-muted-foreground">Charlie streaming...</div>
          ) : null}
        </div>
      </div>

      {chat.error ? <p className="mt-3 text-sm text-destructive">{chat.error}</p> : null}

      <form className="mt-4 space-y-3" onSubmit={(event) => void chat.sendMessage(event)}>
        <Textarea
          disabled={chat.isSending}
          onChange={(event) => chat.setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault()
              void chat.sendMessage()
            }
          }}
          placeholder="Message Charlie"
          value={chat.input}
        />
        <div className="flex justify-end">
          <Button disabled={!chat.canSend} type="submit">
            {chat.isSending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            Send
          </Button>
        </div>
      </form>
    </section>
  )
}

function useCharlieChat() {
  const [messages, setMessages] = useState<CharlieMessage[]>(initialMessages)
  const [input, setInput] = useState("")
  const [error, setError] = useState("")
  const [isSending, setIsSending] = useState(false)
  const canSend = useMemo(() => input.trim().length > 0 && !isSending, [input, isSending])

  const sendMessage = useCallback(
    async (event?: { preventDefault: () => void }) => {
      event?.preventDefault()
      if (!canSend) return

      const requestMessages = [...messages, { role: "user" as const, content: input.trim() }]
      const assistantIndex = requestMessages.length

      setInput("")
      setError("")
      setIsSending(true)
      setMessages([...requestMessages, { role: "assistant", content: "" }])

      try {
        const reply = await streamCharlieChat({
          messages: requestMessages,
          onText: (content) => {
            setMessages((current) =>
              current.map((message, index) =>
                index === assistantIndex ? { role: "assistant", content } : message,
              ),
            )
          },
        })
        setMessages((current) =>
          current.map((message, index) =>
            index === assistantIndex
              ? { role: "assistant", content: reply || "Charlie returned no content." }
              : message,
          ),
        )
      } catch (err) {
        setError(err instanceof Error ? err.message : "charlie chat request failed")
        setMessages(requestMessages)
      } finally {
        setIsSending(false)
      }
    },
    [canSend, input, messages],
  )

  return { messages, input, error, isSending, canSend, setInput, sendMessage }
}

function MessageBubble({ message }: { message: CharlieMessage }) {
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
          {isUser ? "user" : "charlie"}
        </div>
        <div className="whitespace-pre-wrap break-words">{message.content || "..."}</div>
      </div>
    </div>
  )
}
