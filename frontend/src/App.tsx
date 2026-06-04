import { useState, useRef, useEffect, useCallback } from "react";
import { WelcomeScreen } from "./components/WelcomeScreen";
import { ChatMessagesView } from "./components/ChatMessagesView";
import { InputForm } from "./components/InputForm";
import { ActivityTimeline } from "./components/ActivityTimeline";
import { AuditDashboard } from "./components/AuditDashboard";
import {
  createSession,
  streamAgentResponse,
  type ParsedSSEChunk,
  type AuditResult,
  parseAuditReport,
  type AgentId,
} from "./lib/utils";

export interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  agent?: string;
  timestamp: Date;
}

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeAgent, setActiveAgent] = useState<AgentId | null>(null);
  const [agentHistory, setAgentHistory] = useState<AgentId[]>([]);
  const [auditResult, setAuditResult] = useState<AuditResult | null>(null);
  const [showDashboard, setShowDashboard] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const ensureSession = useCallback(async () => {
    if (sessionId) return sessionId;
    const { sessionId: sid } = await createSession();
    setSessionId(sid);
    return sid;
  }, [sessionId]);

  const detectAgentFromContent = (text: string): AgentId | null => {
    const lower = text.toLowerCase();
    if (lower.includes("scope") && (lower.includes("analyz") || lower.includes("assess")))
      return "scope_analyzer";
    if (lower.includes("platform") && lower.includes("detect"))
      return "platform_detector";
    if (lower.includes("scanning") || lower.includes("scan"))
      return "a11y_scanner";
    if (lower.includes("evaluat") || lower.includes("severity"))
      return "a11y_evaluator";
    if (lower.includes("targeted") || lower.includes("deep scan"))
      return "targeted_scanner";
    if (lower.includes("report") || lower.includes("compos"))
      return "audit_report_composer";
    return null;
  };

  const sendMessage = useCallback(
    async (text: string) => {
      if (isStreaming) return;

      const userMsg: Message = {
        id: `u_${Date.now()}`,
        role: "user",
        content: text,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      setAuditResult(null);
      setShowDashboard(false);
      setAgentHistory([]);

      try {
        const sid = await ensureSession();
        const controller = new AbortController();
        abortRef.current = controller;

        let agentContent = "";
        let currentAgent: AgentId | null = null;
        const agentMsgId = `a_${Date.now()}`;

        // Add placeholder agent message
        setMessages((prev) => [
          ...prev,
          { id: agentMsgId, role: "agent", content: "", timestamp: new Date() },
        ]);

        for await (const chunk of streamAgentResponse(sid, text, undefined, undefined, controller.signal)) {
          if (chunk.type === "done") break;

          if (chunk.type === "text" && chunk.content) {
            agentContent += chunk.content;

            // Detect agent changes
            const detected = detectAgentFromContent(chunk.content);
            if (detected && detected !== currentAgent) {
              currentAgent = detected;
              setActiveAgent(detected);
              setAgentHistory((prev) =>
                prev.includes(detected) ? prev : [...prev, detected],
              );
            }

            setMessages((prev) =>
              prev.map((m) =>
                m.id === agentMsgId
                  ? { ...m, content: agentContent, agent: currentAgent ?? undefined }
                  : m,
              ),
            );
          }

          // Try to detect a JSON audit report in the accumulated text
          const jsonMatch = agentContent.match(/```json\s*([\s\S]*?)```/);
          if (jsonMatch) {
            const parsed = parseAuditReport(jsonMatch[1]);
            if (parsed && parsed.findings.length > 0) {
              setAuditResult(parsed);
            }
          }
        }

        // Mark all agents as completed
        setActiveAgent(null);
        setShowDashboard(true);
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setMessages((prev) => [
            ...prev,
            {
              id: `err_${Date.now()}`,
              role: "agent",
              content: `Error: ${err.message}`,
              timestamp: new Date(),
            },
          ]);
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [isStreaming, ensureSession],
  );

  const stopStreaming = () => {
    abortRef.current?.abort();
    setIsStreaming(false);
    setActiveAgent(null);
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="flex h-screen flex-col bg-zinc-950">
      {/* Header */}
      <header className="flex items-center gap-3 border-b border-zinc-800 px-6 py-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand/20 text-brand">
          ♿
        </div>
        <h1 className="text-lg font-semibold">ePost A11y Agent</h1>
        <span className="text-xs text-zinc-500">Accessibility Audit Dashboard</span>
        {isStreaming && (
          <button
            onClick={stopStreaming}
            className="ml-auto rounded-md border border-zinc-700 px-3 py-1 text-xs text-zinc-400 hover:bg-zinc-800"
          >
            Stop
          </button>
        )}
        {showDashboard && auditResult && (
          <button
            onClick={() => setShowDashboard((v) => !v)}
            className="ml-auto rounded-md bg-brand/20 px-3 py-1 text-xs text-brand-light hover:bg-brand/30"
          >
            {showDashboard ? "Show Chat" : "Show Dashboard"}
          </button>
        )}
      </header>

      {/* Main content */}
      {!hasMessages ? (
        <WelcomeScreen onSubmit={sendMessage} />
      ) : (
        <div className="flex flex-1 overflow-hidden">
          {/* Left sidebar – Activity Timeline */}
          <ActivityTimeline
            agentHistory={agentHistory}
            activeAgent={activeAgent}
          />

          {/* Center – Chat or Dashboard */}
          <div className="flex flex-1 flex-col overflow-hidden">
            {showDashboard && auditResult ? (
              <AuditDashboard result={auditResult} />
            ) : (
              <ChatMessagesView messages={messages} isStreaming={isStreaming} />
            )}
            <InputForm
              onSubmit={sendMessage}
              isStreaming={isStreaming}
              onStop={stopStreaming}
            />
          </div>
        </div>
      )}
    </div>
  );
}
