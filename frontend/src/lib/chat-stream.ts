export type ChatRole = "user" | "assistant"

export type ChatMessage = {
  role: ChatRole
  content: string
}

type ChatStreamEvent =
  | { type: "text"; delta: string }
  | { type: "tool_call"; name?: string; arguments?: unknown }
  | { type: "tool_result"; name?: string; content?: unknown }
  | { type: "done" }

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>

export type ChatStreamOptions = {
  agent: string
  messages: ChatMessage[]
  onText: (content: string) => void
  fetchImpl?: FetchLike
  signal?: AbortSignal
}

export async function chatStream({
  agent,
  messages,
  onText,
  fetchImpl = fetch,
  signal,
}: ChatStreamOptions): Promise<string> {
  const response = await fetchImpl(`/agents/${encodeURIComponent(agent)}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
    signal,
  })

  if (!response.ok) {
    throw new Error(`chat request failed: ${response.status}`)
  }

  if (!response.body) {
    throw new Error("chat response body is empty")
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let reply = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split("\n\n")
    buffer = blocks.pop() ?? ""

    for (const block of blocks) {
      const event = parseSseBlock(block)
      if (!event) continue

      if (event.type === "text") {
        reply += event.delta
        onText(reply)
      }

      if (event.type === "done") {
        return reply
      }
    }
  }

  return reply
}

function parseSseBlock(block: string): ChatStreamEvent | null {
  const dataLine = block
    .split("\n")
    .map((line) => line.trim())
    .find((line) => line.startsWith("data: "))

  if (!dataLine) return null
  return JSON.parse(dataLine.slice(6)) as ChatStreamEvent
}
