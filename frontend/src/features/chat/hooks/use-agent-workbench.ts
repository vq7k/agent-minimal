import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import {
  applyAssistantText,
  beginSend,
  canSendMessage,
  createInitialChatState,
  failSend,
  finishAssistant,
  type ChatState,
} from "@/features/chat/chat-state"
import { pickSelectedAgent, type HealthState } from "@/features/chat/runtime"
import { chatStream } from "@/lib/chat-stream"

export type AgentWorkbenchState = ChatState & {
  agents: string[]
  selectedAgent: string
  health: HealthState
  canSend: boolean
}

export type AgentWorkbenchActions = {
  setInput: (input: string) => void
  setSelectedAgent: (agent: string) => void
  refreshRuntime: () => Promise<void>
  sendMessage: () => Promise<void>
}

export function useAgentWorkbench(): AgentWorkbenchState & AgentWorkbenchActions {
  const [agents, setAgents] = useState<string[]>([])
  const [selectedAgent, setSelectedAgent] = useState("")
  const [health, setHealth] = useState<HealthState>("checking")
  const [chatState, setChatState] = useState(createInitialChatState)
  const abortRef = useRef<AbortController | null>(null)

  const canSend = useMemo(
    () => canSendMessage(chatState.input, selectedAgent, chatState.isSending),
    [chatState.input, chatState.isSending, selectedAgent],
  )

  const refreshRuntime = useCallback(async () => {
    setHealth("checking")
    setChatState((state) => ({ ...state, error: "" }))

    try {
      const [healthResponse, agentsResponse] = await Promise.all([fetch("/healthz"), fetch("/agents")])
      if (!healthResponse.ok || !agentsResponse.ok) {
        throw new Error("runtime check failed")
      }

      const data = (await agentsResponse.json()) as { agents: string[] }
      setAgents(data.agents)
      setSelectedAgent((current) => pickSelectedAgent(current, data.agents))
      setHealth("ok")
    } catch {
      setHealth("error")
      setChatState((state) => ({
        ...state,
        error: "后端不可用。确认 uvicorn 正在 8000 端口运行，或线上服务健康。",
      }))
    }
  }, [])

  const sendMessage = useCallback(async () => {
    if (!canSend) return

    const started = beginSend(chatState)
    setChatState(started.state)

    const abortController = new AbortController()
    abortRef.current = abortController

    try {
      const reply = await chatStream({
        agent: selectedAgent,
        messages: started.requestMessages,
        signal: abortController.signal,
        onText: (content) => {
          setChatState((state) => applyAssistantText(state, started.assistantIndex, content))
        },
      })
      setChatState((state) => finishAssistant(state, started.assistantIndex, reply))
    } catch (err) {
      const message = err instanceof Error ? err.message : "chat request failed"
      setChatState((state) => failSend(state, started.requestMessages, message))
    } finally {
      abortRef.current = null
    }
  }, [canSend, chatState, selectedAgent])

  const updateInput = useCallback((input: string) => {
    setChatState((state) => ({ ...state, input }))
  }, [])

  useEffect(() => {
    void refreshRuntime()

    return () => {
      abortRef.current?.abort()
    }
  }, [refreshRuntime])

  return {
    ...chatState,
    agents,
    selectedAgent,
    health,
    canSend,
    setInput: updateInput,
    setSelectedAgent,
    refreshRuntime,
    sendMessage,
  }
}
