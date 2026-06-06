export type AlphaRole = "user" | "assistant"

export type AlphaMessage = {
  role: AlphaRole
  content: string
}

export type StreamAlphaChatOptions = {
  messages: AlphaMessage[]
  onText: (content: string) => void
  fetchImpl?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  signal?: AbortSignal
}

export type StreamAlphaConversationChatOptions = {
  conversationId: string
  message: string
  onText: (content: string) => void
  fetchImpl?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  signal?: AbortSignal
}

export type FetchAlphaConversationMessagesOptions = {
  conversationId: string
  fetchImpl?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  signal?: AbortSignal
}
