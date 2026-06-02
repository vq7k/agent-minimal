export type BravoRole = "user" | "assistant"

export type BravoMessage = {
  role: BravoRole
  content: string
}

export type StreamBravoChatOptions = {
  messages: BravoMessage[]
  onText: (content: string) => void
  fetchImpl?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  signal?: AbortSignal
}
