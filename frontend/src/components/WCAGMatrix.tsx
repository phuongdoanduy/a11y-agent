import { cn } from "../lib/utils";

interface Props {
  coverage: Record<string, number>;
}

// Group WCAG criteria by principle
const WCAG_PRINCIPLES = [
  {
    id: "perceivable",
    label: "Perceivable",
    criteria: ["1.1.1", "1.2.1", "1.2.2", "1.2.3", "1.3.1", "1.3.2", "1.3.3", "1.4.1", "1.4.2", "1.4.3", "1.4.4", "1.4.5", "1.4.11", "1.4.12", "1.4.13"],
  },
  {
    id: "operable",
    label: "Operable",
    criteria: ["2.1.1", "2.1.2", "2.1.4", "2.2.1", "2.2.2", "2.3.1", "2.4.1", "2.4.2", "2.4.3", "2.4.4", "2.4.6", "2.4.7", "2.5.1", "2.5.2", "2.5.3", "2.5.4"],
  },
  {
    id: "understandable",
    label: "Understandable",
    criteria: ["3.1.1", "3.1.2", "3.2.1", "3.2.2", "3.2.3", "3.2.4", "3.3.1", "3.3.2", "3.3.3", "3.3.4"],
  },
  {
    id: "robust",
    label: "Robust",
    criteria: ["4.1.1", "4.1.2", "4.1.3"],
  },
];

export function WCAGMatrix({ coverage }: Props) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5">
      <h3 className="mb-4 text-sm font-semibold text-zinc-300">WCAG 2.1 Coverage</h3>

      <div className="space-y-5">
        {WCAG_PRINCIPLES.map((principle) => (
          <div key={principle.id}>
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-500">
              {principle.label}
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {principle.criteria.map((criterion) => {
                const count = coverage[criterion] ?? 0;
                const hasIssues = count > 0;

                return (
                  <div
                    key={criterion}
                    title={`${criterion}: ${count} issue${count !== 1 ? "s" : ""}`}
                    className={cn(
                      "flex h-8 min-w-[3rem] items-center justify-center rounded-md border px-1.5 text-xs font-mono transition-colors",
                      hasIssues
                        ? count >= 3
                          ? "border-red-500/40 bg-red-500/20 text-red-400"
                          : count >= 2
                            ? "border-orange-500/40 bg-orange-500/20 text-orange-400"
                            : "border-yellow-500/40 bg-yellow-500/20 text-yellow-400"
                        : "border-zinc-700 bg-zinc-800/50 text-zinc-500",
                    )}
                  >
                    {criterion}
                    {hasIssues && (
                      <span className="ml-1 text-[10px]">×{count}</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 flex items-center gap-3 text-xs text-zinc-500">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-sm border border-zinc-700 bg-zinc-800/50" />
          No issues
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-sm bg-yellow-500/30" />
          1 issue
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-sm bg-orange-500/30" />
          2 issues
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-sm bg-red-500/30" />
          3+ issues
        </span>
      </div>
    </div>
  );
}
