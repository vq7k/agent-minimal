import { describe, expect, it, vi } from "vitest"

import { chatStream } from "./chat-stream"

describe("chatStream", () => {
  it("posts messages and emits text deltas from an SSE stream", async () => {
    const stream = new ReadableStream({
      start(controller) {
        const encoder = new TextEncoder()
        controller.enqueue(encoder.encode('data: {"type":"text","delta":"你"}\n\n'))
        controller.enqueue(encoder.encode('data: {"type":"text","delta":"好"}\n\n'))
        controller.enqueue(encoder.encode('data: {"type":"done"}\n\n'))
        controller.close()
      },
    })
    const fetchMock = vi.fn().mockResolvedValue(new Response(stream, { status: 200 }))

    const deltas: string[] = []
    const result = await chatStream({
      agent: "alpha",
      messages: [{ role: "user", content: "hi" }],
      fetchImpl: fetchMock,
      onText: (content) => deltas.push(content),
    })

    expect(fetchMock).toHaveBeenCalledWith(
      "/agents/alpha/chat",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [{ role: "user", content: "hi" }] }),
      }),
    )
    expect(deltas).toEqual(["你", "你好"])
    expect(result).toBe("你好")
  })
})
