import { useState } from "react";

interface Props {
  onSubmit: (text: string) => void;
}

const EXAMPLE_PROMPTS = [
  "Audit https://epost.no for WCAG 2.1 AA compliance on web and iOS",
  "Run accessibility scan on https://epost.no/login – focus on keyboard navigation and screen reader support",
  "Full accessibility audit of https://epost.no covering WCAG 2.1 Level AA for web, Android, and iOS",
];

export function WelcomeScreen({ onSubmit }: Props) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      onSubmit(input.trim());
    }
  };

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4">
      <div className="mx-auto max-w-2xl text-center">
        <div className="mb-6 text-6xl">♿</div>
        <h2 className="mb-3 text-3xl font-bold text-zinc-100">
          Accessibility Audit Agent
        </h2>
        <p className="mb-10 text-zinc-400">
          Enter a URL or audit scope to begin a comprehensive WCAG accessibility
          audit powered by AI agents.
        </p>

        <form onSubmit={handleSubmit} className="mb-8">
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Enter URL or describe your audit scope…"
              className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              className="rounded-lg bg-brand px-6 py-3 text-sm font-medium text-white hover:bg-brand-light disabled:opacity-40"
            >
              Start Audit
            </button>
          </div>
        </form>

        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
            Try an example
          </p>
          <div className="flex flex-col gap-2">
            {EXAMPLE_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                onClick={() => onSubmit(prompt)}
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
