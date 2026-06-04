import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ── ADK SSE helpers ──────────────────────────────────────────────

export interface ADKEvent {
  id?: string;
  type: string;
  content?: string;
  author?: string;
  timestamp?: string;
  metadata?: Record<string, unknown>;
}

export interface ParsedSSEChunk {
  type: "text" | "tool_call" | "tool_result" | "agent_change" | "done" | "error";
  agent?: string;
  content?: string;
  data?: unknown;
}

const API_BASE = "/api";

/** Create a new ADK session */
export async function createSession(userId = "u_999", appName = "app") {
  const sessionId = `s_${Date.now()}`;
  const res = await fetch(
    `${API_BASE}/apps/${appName}/users/${userId}/sessions/${sessionId}`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }
  );
  if (!res.ok) throw new Error(`Session creation failed: ${res.status}`);
  return { sessionId, userId, appName };
}

/** Stream agent response via SSE */
export async function* streamAgentResponse(
  sessionId: string,
  message: string,
  userId = "u_999",
  appName = "app",
  signal?: AbortSignal,
): AsyncGenerator<ParsedSSEChunk> {
  const res = await fetch(`${API_BASE}/run_sse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      app_name: appName,
      user_id: userId,
      session_id: sessionId,
      new_message: {
        role: "user",
        parts: [{ text: message }],
      },
    }),
    signal,
  });

  if (!res.ok) throw new Error(`SSE request failed: ${res.status}`);
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (!raw || raw === "[DONE]") {
        yield { type: "done" };
        return;
      }
      try {
        const event = JSON.parse(raw) as ADKEvent;
        const chunk = parseADKEvent(event);
        if (chunk) yield chunk;
      } catch {
        // skip unparseable lines
      }
    }
  }
  yield { type: "done" };
}

function parseADKEvent(event: ADKEvent): ParsedSSEChunk | null {
  const agent = event.author ?? "agent";

  // Extract text content from parts array
  if (event.type === "text" || (event as any).content?.parts) {
    const parts = (event as any).content?.parts;
    if (Array.isArray(parts)) {
      const textParts = parts
        .filter((p: any) => p.text)
        .map((p: any) => p.text)
        .join("");
      if (textParts) return { type: "text", agent, content: textParts };
    }
    if (event.content && typeof event.content === "string") {
      return { type: "text", agent, content: event.content };
    }
  }

  if (event.type === "functionCall" || event.type === "tool_call") {
    return { type: "tool_call", agent, data: (event as any).content ?? event.metadata };
  }

  if (event.type === "functionResponse" || event.type === "tool_result") {
    return { type: "tool_result", agent, data: (event as any).content ?? event.metadata };
  }

  return { type: "text", agent, content: JSON.stringify(event) };
}

// ── Agent pipeline definitions ───────────────────────────────────

export const AGENT_PIPELINE = [
  { id: "scope_analyzer", label: "Scope Analyzer", icon: "🔍", description: "Analyzing audit scope and requirements" },
  { id: "platform_detector", label: "Platform Detector", icon: "🖥️", description: "Detecting target platform(s)" },
  { id: "a11y_scanner", label: "A11y Scanner", icon: "🔬", description: "Scanning for accessibility issues" },
  { id: "a11y_evaluator", label: "A11y Evaluator", icon: "⚖️", description: "Evaluating severity & WCAG criteria" },
  { id: "targeted_scanner", label: "Targeted Scanner", icon: "🎯", description: "Running targeted deep scans" },
  { id: "audit_report_composer", label: "Report Composer", icon: "📄", description: "Composing final audit report" },
] as const;

export type AgentId = (typeof AGENT_PIPELINE)[number]["id"];

// ── Severity helpers ─────────────────────────────────────────────

export type Severity = "critical" | "serious" | "moderate" | "minor";

export const SEVERITY_CONFIG: Record<Severity, { color: string; bg: string; label: string }> = {
  critical: { color: "text-red-400", bg: "bg-red-500/20 border-red-500/30", label: "Critical" },
  serious:  { color: "text-orange-400", bg: "bg-orange-500/20 border-orange-500/30", label: "Serious" },
  moderate: { color: "text-yellow-400", bg: "bg-yellow-500/20 border-yellow-500/30", label: "Moderate" },
  minor:    { color: "text-green-400", bg: "bg-green-500/20 border-green-500/30", label: "Minor" },
};

// ── Audit result types ───────────────────────────────────────────

export interface Finding {
  id: string;
  title: string;
  severity: Severity;
  wcagCriteria: string[];
  platform: string;
  element: string;
  description: string;
  impact: string;
  fix: {
    description: string;
    codeBefore?: string;
    codeAfter?: string;
  };
}

export interface AuditResult {
  score: number;
  totalFindings: number;
  severityBreakdown: Record<Severity, number>;
  wcagCoverage: Record<string, number>;
  findings: Finding[];
}

/** Parse a JSON audit report string into structured data */
export function parseAuditReport(json: string): AuditResult | null {
  try {
    const data = JSON.parse(json);
    return {
      score: data.score ?? 0,
      totalFindings: data.totalFindings ?? data.findings?.length ?? 0,
      severityBreakdown: data.severityBreakdown ?? { critical: 0, serious: 0, moderate: 0, minor: 0 },
      wcagCoverage: data.wcagCoverage ?? {},
      findings: data.findings ?? [],
    };
  } catch {
    return null;
  }
}
