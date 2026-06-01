import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react"
import { Bot, CheckCircle2, Loader2, RefreshCw, Send, Terminal, WifiOff } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { chatStream, type ChatMessage } from "@/lib/chat-stream"
import { cn } from "@/lib/utils"

type HealthState = "checking" | "ok" | "error"

const starterMessages: ChatMessage[] = [
  {
    role: "assistant",
    content: "选择一个 agent，输入消息后发送。前端会通过 POST SSE 流式接收回复。",
  },
]

function App() {
  const [agents, setAgents] = useState<string[]>([])
  const [selectedAgent, setSelectedAgent] = useState("")
  const [health, setHealth] = useState<HealthState>("checking")
  const [messages, setMessages] = useState<ChatMessage[]>(starterMessages)
  const [input, setInput] = useState("")
  const [error, setError] = useState("")
  const [isSending, setIsSending] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const canSend = input.trim().length > 0 && selectedAgent.length > 0 && !isSending

  const healthBadge = useMemo(() => {
    if (health === "ok") return { label: "online", variant: "secondary" as const, icon: CheckCircle2 }
    if (health === "error") return { label: "offline", variant: "destructive" as const, icon: WifiOff }
    return { label: "checking", variant: "outline" as const, icon: Loader2 }
  }, [health])

  useEffect(() => {
    void refreshRuntime()

    return () => {
      abortRef.current?.abort()
    }
  }, [])

  async function refreshRuntime() {
    setHealth("checking")
    setError("")
    try {
      const [healthResponse, agentsResponse] = await Promise.all([fetch("/healthz"), fetch("/agents")])
      if (!healthResponse.ok || !agentsResponse.ok) {
        throw new Error("runtime check failed")
      }
      const data = (await agentsResponse.json()) as { agents: string[] }
      setAgents(data.agents)
      setSelectedAgent((current) => current || data.agents[0] || "")
      setHealth("ok")
    } catch {
      setHealth("error")
      setError("后端不可用。确认 uvicorn 正在 8000 端口运行，或线上服务健康。")
    }
  }

  async function handleSubmit(event?: FormEvent) {
    event?.preventDefault()
    if (!canSend) return

    const userMessage: ChatMessage = { role: "user", content: input.trim() }
    const nextMessages = [...messages, userMessage]
    const assistantIndex = nextMessages.length

    setInput("")
    setError("")
    setIsSending(true)
    setMessages([...nextMessages, { role: "assistant", content: "" }])

    const abortController = new AbortController()
    abortRef.current = abortController

    try {
      const reply = await chatStream({
        agent: selectedAgent,
        messages: nextMessages,
        signal: abortController.signal,
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
          index === assistantIndex ? { role: "assistant", content: reply || "本轮没有返回内容。" } : message,
        ),
      )
    } catch (err) {
      const message = err instanceof Error ? err.message : "chat request failed"
      setError(message)
      setMessages(nextMessages)
    } finally {
      setIsSending(false)
      abortRef.current = null
    }
  }

  function handleInputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      void handleSubmit()
    }
  }

  const HealthIcon = healthBadge.icon

  return (
    <TooltipProvider>
      <main className="min-h-screen bg-background">
        <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-5 md:px-6">
          <header className="flex flex-col gap-4 border-b pb-4 md:flex-row md:items-center md:justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Bot className="h-5 w-5" aria-hidden="true" />
                <h1 className="text-xl font-semibold tracking-normal">Agent Minimal</h1>
              </div>
              <p className="text-sm text-muted-foreground">Multi-agent SSE chat workbench</p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={healthBadge.variant} className="gap-1.5">
                <HealthIcon className={cn("h-3.5 w-3.5", health === "checking" && "animate-spin")} />
                {healthBadge.label}
              </Badge>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="outline" size="icon" onClick={() => void refreshRuntime()}>
                    <RefreshCw className="h-4 w-4" />
                    <span className="sr-only">刷新运行状态</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>刷新运行状态</TooltipContent>
              </Tooltip>
            </div>
          </header>

          <section className="grid flex-1 grid-cols-1 gap-5 py-5 lg:grid-cols-[260px_1fr]">
            <aside className="space-y-4 border-b pb-5 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-5">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="agent-select">
                  Agent
                </label>
                <Select value={selectedAgent} onValueChange={setSelectedAgent} disabled={agents.length === 0}>
                  <SelectTrigger id="agent-select">
                    <SelectValue placeholder="选择 agent" />
                  </SelectTrigger>
                  <SelectContent>
                    {agents.map((agent) => (
                      <SelectItem key={agent} value={agent}>
                        {agent}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Separator />

              <div className="space-y-2 text-sm text-muted-foreground">
                <div className="flex items-center gap-2 font-medium text-foreground">
                  <Terminal className="h-4 w-4" />
                  Runtime
                </div>
                <p>API: /agents/{selectedAgent || ":name"}/chat</p>
                <p>Mode: POST + SSE streaming</p>
              </div>
            </aside>

            <div className="flex min-h-[620px] flex-col">
              <ScrollArea className="min-h-0 flex-1 rounded-md border">
                <div className="space-y-4 p-4">
                  {messages.map((message, index) => (
                    <MessageBubble key={`${message.role}-${index}`} message={message} />
                  ))}
                  {isSending && messages.at(-1)?.content === "" ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      streaming...
                    </div>
                  ) : null}
                </div>
              </ScrollArea>

              {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}

              <form className="mt-4 space-y-3" onSubmit={(event) => void handleSubmit(event)}>
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
          </section>
        </div>
      </main>
    </TooltipProvider>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
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

export default App
