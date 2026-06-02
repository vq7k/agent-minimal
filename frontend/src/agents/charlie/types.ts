export type CharlieRole = "user" | "assistant"

export type CharlieMessage = {
  role: CharlieRole
  content: string
}

export type StreamCharlieChatOptions = {
  messages: CharlieMessage[]
  onText: (content: string) => void
  fetchImpl?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  signal?: AbortSignal
}
