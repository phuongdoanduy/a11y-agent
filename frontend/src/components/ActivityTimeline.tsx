import { AGENT_PIPELINE, type AgentId, cn } from "../lib/utils";

interface Props {
  agentHistory: AgentId[];
  activeAgent: AgentId | null;
}

export function ActivityTimeline({ agentHistory, activeAgent }: Props) {
  return (
    <aside className="hidden w-64 shrink-0 border-r border-zinc-800 bg-zinc-900/50 p-4 lg:block">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-zinc-500">
        Agent Pipeline
      </h3>
      <div className="space-y-1">
        {AGENT_PIPELINE.map((agent, i) => {
          const isActive = activeAgent === agent.id;
          const isCompleted =
            agentHistory.includes(agent.id) && !isActive;
          const isPending = !agentHistory.includes(agent.id) && !isActive;

          return (
            <div key={agent.id} className="flex items-start gap-3">
              {/* Vertical connector line */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-full text-xs transition-all",
                    isActive && "bg-brand/30 text-brand-light ring-2 ring-brand/50 animate-pulse",
                    isCompleted && "bg-green-500/20 text-green-400",
                    isPending && "bg-zinc-800 text-zinc-600",
                  )}
                >
                  {isCompleted ? "✓" : agent.icon}
                </div>
                {i < AGENT_PIPELINE.length - 1 && (
                  <div
                    className={cn(
                      "w-px h-5",
                      isCompleted ? "bg-green-500/40" : "bg-zinc-800",
                    )}
                  />
                )}
              </div>

              <div className="min-w-0 pt-0.5">
                <p
                  className={cn(
                    "text-sm font-medium truncate",
                    isActive && "text-brand-light",
                    isCompleted && "text-green-400",
                    isPending && "text-zinc-500",
                  )}
                >
                  {agent.label}
                </p>
                {isActive && (
                  <p className="text-xs text-zinc-500 animate-pulse">
                    {agent.description}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
