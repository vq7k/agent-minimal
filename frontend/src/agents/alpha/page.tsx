import { useCallback, useEffect, useMemo, useState } from "react"
import { History, Loader2, Plus, Send } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

import {
  fetchAlphaConversationMessages,
  fetchAlphaConversations,
  streamAlphaConversationChat,
} from "./api"
import type { AlphaConversation, AlphaMessage } from "./types"

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
        <ConversationList
          conversations={chat.conversations}
          currentConversationId={chat.conversationId}
          disabled={chat.isSending || chat.isLoadingHistory}
          isLoading={chat.isLoadingConversations}
          onSelect={chat.openConversation}
        />
        {chat.conversationListError ? (
          <p className="mt-2 text-xs text-destructive">{chat.conversationListError}</p>
        ) : null}
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
  const [conversations, setConversations] = useState<AlphaConversation[]>([])
  const [messages, setMessages] = useState<AlphaMessage[]>(initialMessages)
  const [input, setInput] = useState("")
  const [error, setError] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [isLoadingConversations, setIsLoadingConversations] = useState(false)
  const [conversationListError, setConversationListError] = useState("")
  const canSend = useMemo(
    () => input.trim().length > 0 && !isSending && !isLoadingHistory,
    [input, isLoadingHistory, isSending],
  )

  const refreshConversations = useCallback(async (signal?: AbortSignal) => {
    setIsLoadingConversations(true)
    setConversationListError("")

    try {
      setConversations(await fetchAlphaConversations({ signal }))
    } catch (err) {
      if (signal?.aborted) return
      setConversationListError(err instanceof Error ? err.message : "读取 alpha 会话列表失败")
    } finally {
      if (!signal?.aborted) setIsLoadingConversations(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void refreshConversations(controller.signal)

    return () => controller.abort()
  }, [refreshConversations])

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
        void refreshConversations()
      } catch (err) {
        setError(err instanceof Error ? err.message : "alpha chat request failed")
        setMessages(requestMessages)
      } finally {
        setIsSending(false)
      }
    },
    [canSend, conversationId, input, messages, refreshConversations],
  )

  const startNewConversation = useCallback(() => {
    const nextId = createConversationId()
    saveConversationId(nextId)
    setConversationId(nextId)
    setInput("")
    setError("")
    setMessages(initialMessages)
  }, [])

  const openConversation = useCallback(
    (nextId: string) => {
      if (nextId === conversationId) return

      saveConversationId(nextId)
      setConversationId(nextId)
      setInput("")
      setError("")
      setMessages(initialMessages)
    },
    [conversationId],
  )

  return {
    conversationId,
    conversations,
    messages,
    input,
    error,
    isSending,
    isLoadingHistory,
    isLoadingConversations,
    conversationListError,
    canSend,
    setInput,
    sendMessage,
    startNewConversation,
    openConversation,
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

function ConversationList({
  conversations,
  currentConversationId,
  disabled,
  isLoading,
  onSelect,
}: {
  conversations: AlphaConversation[]
  currentConversationId: string
  disabled: boolean
  isLoading: boolean
  onSelect: (conversationId: string) => void
}) {
  if (conversations.length === 0 && !isLoading) return null

  return (
    <div className="mt-3">
      <Separator className="mb-3" />
      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <History className="h-3.5 w-3.5" />
        Recent conversations
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {conversations.map((conversation) => {
          const isCurrent = conversation.conversation_id === currentConversationId

          return (
            <Button
              className={cn(
                "h-auto w-[180px] flex-shrink-0 flex-col items-start justify-start whitespace-normal px-3 py-2 text-left",
                "hover:border-primary/60",
                isCurrent && "border-primary bg-primary/5",
              )}
              disabled={disabled}
              key={conversation.conversation_id}
              onClick={() => onSelect(conversation.conversation_id)}
              type="button"
              variant="outline"
            >
              <span className="w-full truncate font-medium">{conversation.title}</span>
              <span className="mt-1 text-xs text-muted-foreground">
                {formatConversationTime(conversation.updated_at)}
              </span>
            </Button>
          )
        })}
        {isLoading ? (
          <div className="flex w-[180px] flex-shrink-0 items-center gap-2 rounded-md border px-3 py-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading...
          </div>
        ) : null}
      </div>
    </div>
  )
}

function formatConversationTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ""

  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
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
