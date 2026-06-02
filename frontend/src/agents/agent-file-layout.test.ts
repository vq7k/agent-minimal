import { existsSync, readdirSync } from "node:fs"
import { join } from "node:path"

import { describe, expect, it } from "vitest"

const agentsRoot = join(process.cwd(), "src", "agents")
const agentNames = ["alpha", "bravo", "charlie", "delta"]

describe("agent frontend file layout", () => {
  it("keeps each agent to page/api/types files", () => {
    for (const agentName of agentNames) {
      const agentDir = join(agentsRoot, agentName)

      expect(readdirSync(agentDir).sort()).toEqual(["api.ts", "page.tsx", "types.ts"])
      expect(existsSync(join(agentDir, "components"))).toBe(false)
      expect(existsSync(join(agentDir, "useChat.ts"))).toBe(false)
    }
  })
})
