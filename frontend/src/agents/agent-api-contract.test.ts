import { describe, expect, it, vi } from "vitest"

import type { AlphaMessage } from "./alpha/types"
import { streamAlphaChat } from "./alpha/api"
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
})
