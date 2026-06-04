import { useState } from "react";

interface Props {
  onSubmit: (scope: string, targetDir: string) => void;
}

interface ValidationResult {
  ok: boolean;
  fileCount: number;
  platforms: string[];
}

const EXAMPLE_PROMPTS = [
  "Audit the iOS app for WCAG 2.1 AA compliance — focus on VoiceOver and Dynamic Type",
  "Run accessibility scan on the Android app — keyboard navigation and TalkBack support",
  "Full WCAG 2.1 AA audit covering forms, images, and focus management",
];

export function WelcomeScreen({ onSubmit }: Props) {
  const [path, setPath] = useState("");
  const [scope, setScope] = useState("");
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<ValidationResult | null>(null);

  const handleValidate = async () => {
    setValidating(true);
    setValidation(null);
    try {
      const res = await fetch(`/util/validate?path=${encodeURIComponent(path.trim())}`);
      const data = await res.json();
      setValidation({
        ok: data.exists,
        fileCount: data.file_count,
        platforms: data.detected_platforms,
      });
    } catch {
      setValidation({ ok: false, fileCount: 0, platforms: [] });
    } finally {
      setValidating(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (scope.trim() && validation?.ok) {
      onSubmit(scope.trim(), path.trim());
    }
  };

  const canSubmit = scope.trim().length > 0 && validation?.ok === true;

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4">
      <div className="mx-auto max-w-2xl text-center">
        <div className="mb-6 text-6xl">♿</div>
        <h2 className="mb-3 text-3xl font-bold text-zinc-100">
          Accessibility Audit Agent
        </h2>
        <p className="mb-10 text-zinc-400">
          Point the agent at a local project directory, then describe the audit
          scope to begin a comprehensive WCAG 2.1 AA audit powered by AI agents.
        </p>

        <form onSubmit={handleSubmit} className="mb-8">
          {/* Project path row */}
          <div className="mb-4 text-left">
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">
              Local Project Path
            </label>
            <div className="flex gap-2">
              <input
                value={path}
                onChange={(e) => {
                  setPath(e.target.value);
                  setValidation(null);
                }}
                placeholder="/Users/you/my-app"
                className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
              />
              <button
                type="button"
                onClick={handleValidate}
                disabled={!path.trim() || validating}
                className="rounded-lg border border-zinc-700 px-4 py-3 text-sm text-zinc-300 hover:bg-zinc-800 disabled:opacity-40"
              >
                {validating ? "…" : "Validate"}
              </button>
            </div>
            {validation && (
              <p
                className={`mt-1.5 text-xs ${
                  validation.ok ? "text-green-400" : "text-red-400"
                }`}
              >
                {validation.ok
                  ? `✓ ${validation.fileCount.toLocaleString()} files · ${
                      validation.platforms.length > 0
                        ? validation.platforms.join(", ")
                        : "unknown platform"
                    }`
                  : "✗ Path not found or not a directory"}
              </p>
            )}
          </div>

          {/* Scope row */}
          <div className="mb-4 text-left">
            <label className="mb-1.5 block text-xs font-medium text-zinc-400">
              Audit Scope
            </label>
            <div className="flex gap-2">
              <input
                value={scope}
                onChange={(e) => setScope(e.target.value)}
                placeholder="Audit for WCAG 2.1 AA compliance…"
                className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
              />
              <button
                type="submit"
                disabled={!canSubmit}
                className="rounded-lg bg-brand px-6 py-3 text-sm font-medium text-white hover:bg-brand-light disabled:opacity-40"
              >
                Start Audit
              </button>
            </div>
            {!validation?.ok && scope.trim() && (
              <p className="mt-1.5 text-xs text-zinc-500">
                Validate the project path above to enable the audit.
              </p>
            )}
          </div>
        </form>

        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
            Try an example scope
          </p>
          <div className="flex flex-col gap-2">
            {EXAMPLE_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                onClick={() => setScope(prompt)}
                className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-2.5 text-left text-sm text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
