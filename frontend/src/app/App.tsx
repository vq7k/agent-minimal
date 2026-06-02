import { AgentsIndexPage } from "@/app/AgentsIndexPage"
import { agentRoutes, resolveAgentRoute } from "@/app/router"

export function App() {
  const route = resolveAgentRoute(window.location.pathname)

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-4 py-5 md:px-6">
        <header className="flex flex-col gap-4 border-b pb-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <h1 className="text-xl font-semibold tracking-normal">Agent Minimal</h1>
            <p className="text-sm text-muted-foreground">Four independently developed agent frontends</p>
          </div>

          <nav className="flex flex-wrap gap-2" aria-label="Agent pages">
            {agentRoutes.map((item) => (
              <a
                className="rounded-md border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                href={item.path}
                key={item.agent}
              >
                {item.label}
              </a>
            ))}
          </nav>
        </header>

        {route ? <route.Page /> : <AgentsIndexPage />}
      </div>
    </main>
  )
}
