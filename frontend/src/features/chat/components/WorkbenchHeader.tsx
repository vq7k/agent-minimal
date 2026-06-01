import { Bot, CheckCircle2, Loader2, RefreshCw, WifiOff } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import type { HealthState } from "@/features/chat/runtime"
import { cn } from "@/lib/utils"

type WorkbenchHeaderProps = {
  health: HealthState
  refreshRuntime: () => Promise<void>
}

export function WorkbenchHeader({ health, refreshRuntime }: WorkbenchHeaderProps) {
  const healthBadge = getHealthBadge(health)
  const HealthIcon = healthBadge.icon

  return (
    <header className="flex flex-col gap-4 border-b pb-4 md:flex-row md:items-center md:justify-between">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5" aria-hidden="true" />
          <h1 className="text-xl font-semibold tracking-normal">Agent Minimal</h1>
        </div>
        <p className="text-sm text-muted-foreground">Multi-agent SSE chat workbench</p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={healthBadge.variant} className="gap-1.5">
          <HealthIcon className={cn("h-3.5 w-3.5", health === "checking" && "animate-spin")} />
          {healthBadge.label}
        </Badge>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="outline" size="icon" onClick={() => void refreshRuntime()}>
              <RefreshCw className="h-4 w-4" />
              <span className="sr-only">刷新运行状态</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent>刷新运行状态</TooltipContent>
        </Tooltip>
      </div>
    </header>
  )
}

function getHealthBadge(health: HealthState) {
  if (health === "ok") return { label: "online", variant: "secondary" as const, icon: CheckCircle2 }
  if (health === "error") return { label: "offline", variant: "destructive" as const, icon: WifiOff }
  return { label: "checking", variant: "outline" as const, icon: Loader2 }
}
