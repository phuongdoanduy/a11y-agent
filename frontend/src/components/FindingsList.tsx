import { useState } from "react";
import type { Finding, Severity } from "../lib/utils";
import { SEVERITY_CONFIG } from "../lib/utils";
import { SeverityBadge } from "./SeverityBadge";

interface Props {
  findings: Finding[];
}

export function FindingsList({ findings }: Props) {
  const [severityFilter, setSeverityFilter] = useState<Severity | "all">("all");
  const [platformFilter, setPlatformFilter] = useState<string>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const platforms = [...new Set(findings.map((f) => f.platform))].filter(Boolean);

  const filtered = findings.filter((f) => {
    if (severityFilter !== "all" && f.severity !== severityFilter) return false;
    if (platformFilter !== "all" && f.platform !== platformFilter) return false;
    return true;
  });

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h3 className="text-sm font-semibold text-zinc-300">
          Findings ({filtered.length})
        </h3>

        {/* Severity filter */}
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value as Severity | "all")}
          className="rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs text-zinc-300"
        >
          <option value="all">All severities</option>
          {(["critical", "serious", "moderate", "minor"] as Severity[]).map((s) => (
            <option key={s} value={s}>
              {SEVERITY_CONFIG[s].label}
            </option>
          ))}
        </select>

        {/* Platform filter */}
        {platforms.length > 1 && (
          <select
            value={platformFilter}
            onChange={(e) => setPlatformFilter(e.target.value)}
            className="rounded-md border border-zinc-700 bg-zinc-800 px-2 py-1 text-xs text-zinc-300"
          >
            <option value="all">All platforms</option>
            {platforms.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="space-y-2">
        {filtered.length === 0 && (
          <p className="py-8 text-center text-sm text-zinc-500">No findings match filters.</p>
        )}
        {filtered.map((finding) => (
          <FindingCard
            key={finding.id}
            finding={finding}
            isExpanded={expandedId === finding.id}
            onToggle={() => setExpandedId(expandedId === finding.id ? null : finding.id)}
          />
        ))}
      </div>
    </div>
  );
}

function FindingCard({
  finding,
  isExpanded,
  onToggle,
}: {
  finding: Finding;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-800/40 transition-colors hover:border-zinc-700">
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
      >
        <SeverityBadge severity={finding.severity} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-zinc-200">{finding.title}</p>
          <p className="mt-0.5 text-xs text-zinc-500">
            {finding.wcagCriteria?.join(", ")} · {finding.platform}
          </p>
        </div>
        <svg
          className={`h-4 w-4 text-zinc-500 transition-transform ${isExpanded ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="border-t border-zinc-700/50 px-4 py-3 space-y-3">
          <div>
            <p className="text-xs font-medium text-zinc-500">Description</p>
            <p className="mt-1 text-sm text-zinc-300">{finding.description}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-zinc-500">Impact</p>
            <p className="mt-1 text-sm text-zinc-300">{finding.impact}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-zinc-500">Element</p>
            <code className="mt-1 block rounded bg-zinc-800 px-2 py-1 text-xs text-zinc-400">
              {finding.element}
            </code>
          </div>
          {finding.fix && (
            <div>
              <p className="text-xs font-medium text-zinc-500">Suggested Fix</p>
              <p className="mt-1 text-sm text-zinc-300">{finding.fix.description}</p>
              {finding.fix.codeBefore && (
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  <div>
                    <p className="mb-1 text-xs text-red-400">Before</p>
                    <pre className="overflow-x-auto rounded bg-zinc-800 p-2 text-xs text-zinc-400">
                      <code>{finding.fix.codeBefore}</code>
                    </pre>
                  </div>
                  {finding.fix.codeAfter && (
                    <div>
                      <p className="mb-1 text-xs text-green-400">After</p>
                      <pre className="overflow-x-auto rounded bg-zinc-800 p-2 text-xs text-zinc-400">
                        <code>{finding.fix.codeAfter}</code>
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
