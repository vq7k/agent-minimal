import { AgentWorkbenchView } from "@/features/chat/components/AgentWorkbenchView"
import { useAgentWorkbench } from "@/features/chat/hooks/use-agent-workbench"

export function AgentWorkbench() {
  const workbench = useAgentWorkbench()

  return <AgentWorkbenchView workbench={workbench} />
}
