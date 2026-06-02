import type { StreamBravoChatOptions } from "./types"

type BravoStreamEvent = { type: "text"; delta: string } | { type: "done" }

export async function streamBravoChat({
  messages,
  onText,
  fetchImpl = fetch,
  signal,
}: StreamBravoChatOptions): Promise<string> {
  // 这里必须用 fetch 读 ReadableStream:EventSource 只能 GET,不能 POST messages JSON。
  const response = await fetchImpl("/agents/bravo/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
    signal,
  })

  if (!response.ok) throw new Error(`bravo chat request failed: ${response.status}`)
  if (!response.body) throw new Error("bravo chat response body is empty")

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let reply = ""

  // 后端返回 text/event-stream,每个 data block 可能被网络切成半包,所以需要 buffer。
  while (true) {
    const { done, value } = await reader.read()
    if (done) return reply

    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split("\n\n")
    buffer = blocks.pop() ?? ""

    for (const block of blocks) {
      const event = parseBravoEvent(block)
      if (!event) continue
      if (event.type === "done") return reply
      reply += event.delta
      onText(reply)
    }
  }
}

function parseBravoEvent(block: string): BravoStreamEvent | null {
  const dataLine = block
    .split("\n")
    .map((line) => line.trim())
    .find((line) => line.startsWith("data: "))

  if (!dataLine) return null
  return JSON.parse(dataLine.slice(6)) as BravoStreamEvent
}
