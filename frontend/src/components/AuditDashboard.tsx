import type { AuditResult } from "../lib/utils";
import { SEVERITY_CONFIG, type Severity } from "../lib/utils";
import { FindingsList } from "./FindingsList";
import { WCAGMatrix } from "./WCAGMatrix";

interface Props {
  result: AuditResult;
}

export function AuditDashboard({ result }: Props) {
  const { score, totalFindings, severityBreakdown, wcagCoverage, findings } = result;

  const scoreColor =
    score >= 90 ? "text-green-400" : score >= 70 ? "text-yellow-400" : "text-red-400";

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      <div className="mx-auto max-w-5xl space-y-8">
        {/* Score Card */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 text-center">
            <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
              Accessibility Score
            </p>
            <p className={`mt-2 text-5xl font-bold ${scoreColor}`}>{score}</p>
            <p className="mt-1 text-xs text-zinc-500">out of 100</p>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 text-center">
            <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
              Total Findings
            </p>
            <p className="mt-2 text-5xl font-bold text-zinc-100">{totalFindings}</p>
            <p className="mt-1 text-xs text-zinc-500">issues detected</p>
          </div>

          {(Object.keys(severityBreakdown) as Severity[]).map((sev) => (
            <div
              key={sev}
              className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 text-center"
            >
              <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
                {SEVERITY_CONFIG[sev].label}
              </p>
              <p className={`mt-2 text-5xl font-bold ${SEVERITY_CONFIG[sev].color}`}>
                {severityBreakdown[sev]}
              </p>
            </div>
          ))}
        </div>

        {/* Severity Bar */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5">
          <h3 className="mb-3 text-sm font-semibold text-zinc-300">Severity Breakdown</h3>
          <div className="flex h-4 overflow-hidden rounded-full bg-zinc-800">
            {(["critical", "serious", "moderate", "minor"] as Severity[]).map((sev) => {
              const count = severityBreakdown[sev] ?? 0;
              const pct = totalFindings > 0 ? (count / totalFindings) * 100 : 0;
              if (pct === 0) return null;
              const colors: Record<Severity, string> = {
                critical: "bg-red-500",
                serious: "bg-orange-500",
                moderate: "bg-yellow-500",
                minor: "bg-green-500",
              };
              return (
                <div
                  key={sev}
                  className={`${colors[sev]} transition-all`}
                  style={{ width: `${pct}%` }}
                  title={`${SEVERITY_CONFIG[sev].label}: ${count}`}
                />
              );
            })}
          </div>
          <div className="mt-2 flex gap-4 text-xs text-zinc-500">
            {(["critical", "serious", "moderate", "minor"] as Severity[]).map((sev) => (
              <span key={sev} className="flex items-center gap-1.5">
                <span
                  className={`inline-block h-2 w-2 rounded-full ${
                    sev === "critical"
                      ? "bg-red-500"
                      : sev === "serious"
                        ? "bg-orange-500"
                        : sev === "moderate"
                          ? "bg-yellow-500"
                          : "bg-green-500"
                  }`}
                />
                {SEVERITY_CONFIG[sev].label}: {severityBreakdown[sev] ?? 0}
              </span>
            ))}
          </div>
        </div>

        {/* WCAG Coverage Matrix */}
        <WCAGMatrix coverage={wcagCoverage} />

        {/* Findings List */}
        <FindingsList findings={findings} />
      </div>
    </div>
  );
}
