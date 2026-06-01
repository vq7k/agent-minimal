import type { ChatMessage } from "@/lib/chat-stream"

export type ChatState = {
  messages: ChatMessage[]
  input: string
  error: string
  isSending: boolean
}

export const emptyReplyText = "本轮没有返回内容。"

export const starterMessages: ChatMessage[] = [
  {
    role: "assistant",
    content: "选择一个 agent，输入消息后发送。前端会通过 POST SSE 流式接收回复。",
  },
]

export function createInitialChatState(): ChatState {
  return {
    messages: starterMessages,
    input: "",
    error: "",
    isSending: false,
  }
}

export function canSendMessage(input: string, selectedAgent: string, isSending: boolean): boolean {
  return input.trim().length > 0 && selectedAgent.length > 0 && !isSending
}

export function beginSend(state: Pick<ChatState, "messages" | "input">) {
  const userMessage: ChatMessage = { role: "user", content: state.input.trim() }
  const requestMessages = [...state.messages, userMessage]
  const assistantIndex = requestMessages.length

  return {
    requestMessages,
    assistantIndex,
    state: {
      messages: [...requestMessages, { role: "assistant" as const, content: "" }],
      input: "",
      error: "",
      isSending: true,
    },
  }
}

export function applyAssistantText(state: ChatState, assistantIndex: number, content: string): ChatState {
  return {
    ...state,
    messages: replaceMessage(state.messages, assistantIndex, { role: "assistant", content }),
  }
}

export function finishAssistant(state: ChatState, assistantIndex: number, reply: string): ChatState {
  return {
    ...state,
    isSending: false,
    messages: replaceMessage(state.messages, assistantIndex, {
      role: "assistant",
      content: reply || emptyReplyText,
    }),
  }
}

export function failSend(state: ChatState, requestMessages: ChatMessage[], error: string): ChatState {
  return {
    ...state,
    messages: requestMessages,
    error,
    isSending: false,
  }
}

function replaceMessage(
  messages: ChatMessage[],
  targetIndex: number,
  replacement: ChatMessage,
): ChatMessage[] {
  return messages.map((message, index) => (index === targetIndex ? replacement : message))
}
