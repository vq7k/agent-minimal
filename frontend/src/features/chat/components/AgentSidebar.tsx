import { Terminal } from "lucide-react"

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"

type AgentSidebarProps = {
  agents: string[]
  selectedAgent: string
  setSelectedAgent: (agent: string) => void
}

export function AgentSidebar({ agents, selectedAgent, setSelectedAgent }: AgentSidebarProps) {
  return (
    <aside className="space-y-4 border-b pb-5 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-5">
      <div className="space-y-2">
        <label className="text-sm font-medium" htmlFor="agent-select">
          Agent
        </label>
        <Select value={selectedAgent} onValueChange={setSelectedAgent} disabled={agents.length === 0}>
          <SelectTrigger id="agent-select">
            <SelectValue placeholder="选择 agent" />
          </SelectTrigger>
          <SelectContent>
            {agents.map((agent) => (
              <SelectItem key={agent} value={agent}>
                {agent}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Separator />

      <div className="space-y-2 text-sm text-muted-foreground">
        <div className="flex items-center gap-2 font-medium text-foreground">
          <Terminal className="h-4 w-4" />
          Runtime
        </div>
        <p>API: /agents/{selectedAgent || ":name"}/chat</p>
        <p>Mode: POST + SSE streaming</p>
      </div>
    </aside>
  )
}
