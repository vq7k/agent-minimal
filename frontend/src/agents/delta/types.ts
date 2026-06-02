export type DeltaRole = "user" | "assistant"

export type DeltaMessage = {
  role: DeltaRole
  content: string
}

export type StreamDeltaChatOptions = {
  messages: DeltaMessage[]
  onText: (content: string) => void
  fetchImpl?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  signal?: AbortSignal
}
