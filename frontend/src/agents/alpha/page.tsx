import { useCallback, useEffect, useMemo, useState } from "react"
import { Loader2, Plus, Send } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

import { fetchAlphaConversationMessages, streamAlphaConversationChat } from "./api"
import type { AlphaMessage } from "./types"

const initialMessages: AlphaMessage[] = [{ role: "assistant", content: "Alpha ready." }]
const conversationStorageKey = "agent-minimal.alpha.conversation-id"

export function AlphaPage() {
  // 当前页面很小,hook 和小展示函数留在本文件;超过单人可读范围时再拆。
  const chat = useAlphaChat()

  return (
    <section className="flex min-h-[720px] flex-col py-5">
      <div className="mb-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Alpha</h2>
            <p className="text-sm text-muted-foreground">Owned by the Alpha developer.</p>
          </div>
          <Button
            disabled={chat.isSending || chat.isLoadingHistory}
            onClick={chat.startNewConversation}
            type="button"
            variant="outline"
          >
            <Plus className="h-4 w-4" />
            New
          </Button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto rounded-md border p-4">
        <div className="space-y-4">
          {chat.messages.map((message, index) => (
            <MessageBubble key={`${message.role}-${index}`} message={message} />
          ))}
          {chat.isSending && chat.messages.at(-1)?.content === "" ? (
            <div className="text-sm text-muted-foreground">Alpha streaming...</div>
          ) : null}
          {chat.isLoadingHistory ? (
            <div className="text-sm text-muted-foreground">Loading conversation...</div>
          ) : null}
        </div>
      </div>

      {chat.error ? <p className="mt-3 text-sm text-destructive">{chat.error}</p> : null}

      <form className="mt-4 space-y-3" onSubmit={(event) => void chat.sendMessage(event)}>
        <Textarea
          disabled={chat.isSending || chat.isLoadingHistory}
          onChange={(event) => chat.setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault()
              void chat.sendMessage()
            }
          }}
          placeholder="Message Alpha"
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

function useAlphaChat() {
  const [conversationId, setConversationId] = useState(loadConversationId)
  const [messages, setMessages] = useState<AlphaMessage[]>(initialMessages)
  const [input, setInput] = useState("")
  const [error, setError] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const canSend = useMemo(
    () => input.trim().length > 0 && !isSending && !isLoadingHistory,
    [input, isLoadingHistory, isSending],
  )

  useEffect(() => {
    const controller = new AbortController()
    setIsLoadingHistory(true)
    setError("")

    void fetchAlphaConversationMessages({
      conversationId,
      signal: controller.signal,
    })
      .then((history) => {
        setMessages(history.length > 0 ? history : initialMessages)
      })
      .catch((err) => {
        if (controller.signal.aborted) return
        setError(err instanceof Error ? err.message : "读取 alpha 会话历史失败")
        setMessages(initialMessages)
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoadingHistory(false)
      })

    return () => controller.abort()
  }, [conversationId])

  const sendMessage = useCallback(
    async (event?: { preventDefault: () => void }) => {
      event?.preventDefault()
      if (!canSend) return

      const userMessage = input.trim()
      const requestMessages = [...messages, { role: "user" as const, content: userMessage }]
      const assistantIndex = requestMessages.length

      setInput("")
      setError("")
      setIsSending(true)
      setMessages([...requestMessages, { role: "assistant", content: "" }])

      try {
        const reply = await streamAlphaConversationChat({
          conversationId,
          message: userMessage,
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
              ? { role: "assistant", content: reply || "Alpha returned no content." }
              : message,
          ),
        )
      } catch (err) {
        setError(err instanceof Error ? err.message : "alpha chat request failed")
        setMessages(requestMessages)
      } finally {
        setIsSending(false)
      }
    },
    [canSend, conversationId, input, messages],
  )

  const startNewConversation = useCallback(() => {
    const nextId = createConversationId()
    saveConversationId(nextId)
    setConversationId(nextId)
    setInput("")
    setError("")
    setMessages(initialMessages)
  }, [])

  return {
    messages,
    input,
    error,
    isSending,
    isLoadingHistory,
    canSend,
    setInput,
    sendMessage,
    startNewConversation,
  }
}

function loadConversationId() {
  const stored = window.localStorage.getItem(conversationStorageKey)
  if (stored) return stored

  const id = createConversationId()
  saveConversationId(id)
  return id
}

function saveConversationId(id: string) {
  window.localStorage.setItem(conversationStorageKey, id)
}

function createConversationId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID()
  return `alpha-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function MessageBubble({ message }: { message: AlphaMessage }) {
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
          {isUser ? "user" : "alpha"}
        </div>
        <div className="whitespace-pre-wrap break-words">{message.content || "..."}</div>
      </div>
    </div>
  )
}
