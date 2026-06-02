import type { ComponentType } from "react"

import { AlphaPage } from "@/agents/alpha/page"
import { BravoPage } from "@/agents/bravo/page"
import { CharliePage } from "@/agents/charlie/page"
import { DeltaPage } from "@/agents/delta/page"

export type AgentRoute = {
  agent: "alpha" | "bravo" | "charlie" | "delta"
  label: string
  path: string
  Page: ComponentType
}

// 路由显式列出每个 agent 页面,避免一个通用 ChatPage 把 4 个负责人的边界混在一起。
export const agentRoutes: AgentRoute[] = [
  { agent: "alpha", label: "Alpha", path: "/alpha", Page: AlphaPage },
  { agent: "bravo", label: "Bravo", path: "/bravo", Page: BravoPage },
  { agent: "charlie", label: "Charlie", path: "/charlie", Page: CharliePage },
  { agent: "delta", label: "Delta", path: "/delta", Page: DeltaPage },
]

export function resolveAgentRoute(pathname: string): AgentRoute | undefined {
  return agentRoutes.find((route) => route.path === pathname)
}
