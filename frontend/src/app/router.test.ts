import { describe, expect, it } from "vitest"

import { agentRoutes } from "./router"

describe("agent routes", () => {
  it("keeps each agent as a separate page boundary", () => {
    expect(agentRoutes.map((route) => route.agent)).toEqual(["alpha", "bravo", "charlie", "delta"])
    expect(agentRoutes.map((route) => route.path)).toEqual(["/alpha", "/bravo", "/charlie", "/delta"])
  })
})
