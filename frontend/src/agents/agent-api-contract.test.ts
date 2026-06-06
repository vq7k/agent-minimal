import { describe, expect, it, vi } from "vitest"

import type { AlphaMessage } from "./alpha/types"
import {
  fetchAlphaConversationMessages,
  streamAlphaChat,
  streamAlphaConversationChat,
} from "./alpha/api"
import type { BravoMessage } from "./bravo/types"
import { streamBravoChat } from "./bravo/api"
import type { CharlieMessage } from "./charlie/types"
import { streamCharlieChat } from "./charlie/api"
import type { DeltaMessage } from "./delta/types"
import { streamDeltaChat } from "./delta/api"

describe("agent api boundaries", () => {
  it.each([
    ["alpha", streamAlphaChat, [{ role: "user", content: "hi" }] satisfies AlphaMessage[]],
    ["bravo", streamBravoChat, [{ role: "user", content: "hi" }] satisfies BravoMessage[]],
    ["charlie", streamCharlieChat, [{ role: "user", content: "hi" }] satisfies CharlieMessage[]],
    ["delta", streamDeltaChat, [{ role: "user", content: "hi" }] satisfies DeltaMessage[]],
  ])("posts %s messages to its own backend endpoint", async (agent, streamChat, messages) => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        new ReadableStream({
          start(controller) {
            controller.enqueue(new TextEncoder().encode('data: {"type":"done"}\n\n'))
            controller.close()
          },
        }),
      ),
    )

    await streamChat({ messages, onText: vi.fn(), fetchImpl: fetchMock })

    expect(fetchMock).toHaveBeenCalledWith(
      `/agents/${agent}/chat`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ messages }),
      }),
    )
  })

  it("posts alpha conversation messages to the persisted conversation endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        new ReadableStream({
          start(controller) {
            controller.enqueue(new TextEncoder().encode('data: {"type":"text","delta":"ok"}\n\n'))
            controller.enqueue(new TextEncoder().encode('data: {"type":"done"}\n\n'))
            controller.close()
          },
        }),
      ),
    )
    const onText = vi.fn()

    const reply = await streamAlphaConversationChat({
      conversationId: "conv-1",
      message: "hello",
      onText,
      fetchImpl: fetchMock,
    })

    expect(reply).toBe("ok")
    expect(onText).toHaveBeenCalledWith("ok")
    expect(fetchMock).toHaveBeenCalledWith(
      "/agents/alpha/conversations/conv-1/chat",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ message: "hello" }),
      }),
    )
  })

  it("loads alpha persisted conversation messages", async () => {
    const messages = [{ role: "user" as const, content: "hi" }]
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ messages }), {
        headers: { "Content-Type": "application/json" },
      }),
    )

    const result = await fetchAlphaConversationMessages({
      conversationId: "conv-1",
      fetchImpl: fetchMock,
    })

    expect(result).toEqual(messages)
    expect(fetchMock).toHaveBeenCalledWith("/agents/alpha/conversations/conv-1/messages", {
      signal: undefined,
    })
  })
})
