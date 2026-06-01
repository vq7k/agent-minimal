export type HealthState = "checking" | "ok" | "error"

export type RuntimeState = {
  agents: string[]
  selectedAgent: string
  health: HealthState
}

export function pickSelectedAgent(current: string, agents: string[]): string {
  return current || agents[0] || ""
}
