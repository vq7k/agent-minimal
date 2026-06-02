import { agentRoutes } from "@/app/router"

export function AgentsIndexPage() {
  return (
    <section className="grid flex-1 content-start gap-4 py-6 sm:grid-cols-2 lg:grid-cols-4">
      {agentRoutes.map((route) => (
        <a
          className="rounded-md border p-4 shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground"
          href={route.path}
          key={route.agent}
        >
          <div className="text-sm font-medium">{route.label}</div>
          <div className="mt-2 text-sm text-muted-foreground">Open {route.agent} workspace</div>
        </a>
      ))}
    </section>
  )
}
