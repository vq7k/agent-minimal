import { TooltipProvider } from "@/components/ui/tooltip"
import { AgentSidebar } from "@/features/chat/components/AgentSidebar"
import { ConversationPanel } from "@/features/chat/components/ConversationPanel"
import { WorkbenchHeader } from "@/features/chat/components/WorkbenchHeader"
import type { AgentWorkbenchActions, AgentWorkbenchState } from "@/features/chat/hooks/use-agent-workbench"

type AgentWorkbenchViewProps = {
  workbench: AgentWorkbenchState & AgentWorkbenchActions
}

export function AgentWorkbenchView({ workbench }: AgentWorkbenchViewProps) {
  return (
    <TooltipProvider>
      <main className="min-h-screen bg-background">
        <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-5 md:px-6">
          <WorkbenchHeader health={workbench.health} refreshRuntime={workbench.refreshRuntime} />

          <section className="grid flex-1 grid-cols-1 gap-5 py-5 lg:grid-cols-[260px_1fr]">
            <AgentSidebar
              agents={workbench.agents}
              selectedAgent={workbench.selectedAgent}
              setSelectedAgent={workbench.setSelectedAgent}
            />
            <ConversationPanel
              canSend={workbench.canSend}
              error={workbench.error}
              input={workbench.input}
              isSending={workbench.isSending}
              messages={workbench.messages}
              sendMessage={workbench.sendMessage}
              setInput={workbench.setInput}
            />
          </section>
        </div>
      </main>
    </TooltipProvider>
  )
}
