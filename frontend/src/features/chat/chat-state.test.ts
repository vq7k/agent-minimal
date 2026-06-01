import { describe, expect, it } from "vitest"

import { applyAssistantText, beginSend, failSend, finishAssistant } from "./chat-state"

describe("chat state helpers", () => {
  it("starts a send by appending user and pending assistant messages", () => {
    const result = beginSend({
      messages: [{ role: "assistant", content: "ready" }],
      input: "  hi  ",
    })

    expect(result.requestMessages).toEqual([
      { role: "assistant", content: "ready" },
      { role: "user", content: "hi" },
    ])
    expect(result.assistantIndex).toBe(2)
    expect(result.state).toMatchObject({
      input: "",
      error: "",
      isSending: true,
      messages: [
        { role: "assistant", content: "ready" },
        { role: "user", content: "hi" },
        { role: "assistant", content: "" },
      ],
    })
  })

  it("updates and finishes the pending assistant message", () => {
    const state = {
      input: "",
      error: "",
      isSending: true,
      messages: [
        { role: "user" as const, content: "hi" },
        { role: "assistant" as const, content: "" },
      ],
    }

    const streaming = applyAssistantText(state, 1, "你好")
    const finished = finishAssistant(streaming, 1, "")

    expect(streaming.messages[1]).toEqual({ role: "assistant", content: "你好" })
    expect(finished.messages[1]).toEqual({ role: "assistant", content: "本轮没有返回内容。" })
    expect(finished.isSending).toBe(false)
  })

  it("restores messages and records the error when sending fails", () => {
    const state = {
      input: "",
      error: "",
      isSending: true,
      messages: [
        { role: "user" as const, content: "hi" },
        { role: "assistant" as const, content: "" },
      ],
    }
    const requestMessages = [{ role: "user" as const, content: "hi" }]

    expect(failSend(state, requestMessages, "network")).toEqual({
      input: "",
      error: "network",
      isSending: false,
      messages: requestMessages,
    })
  })
})
