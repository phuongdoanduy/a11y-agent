# epost-a11y-agent — Project Overview & Product Development Requirements

## Product Purpose

**epost-a11y-agent** is a multi-platform accessibility auditor that helps developers, QA engineers, and compliance officers detect and fix WCAG 2.1 AA violations across iOS, Android, and Web codebases. Built on Google's Agent Development Kit (ADK) with Gemini 2.5 Pro models, it delivers iterative, human-approved audits with structured findings and remediation guidance.

### Problem Solved

Manual accessibility audits are time-consuming, inconsistent, and error-prone. Teams lack:
- **Automated scanning** for common WCAG violations across platforms
- **Intelligent refinement** — first-pass scans often miss edge cases and platform-specific issues
- **Structured output** — violation IDs, severity levels, fix templates, and PR blocking criteria
- **Human approval loops** — users need control over audit scope before the agent spends resources

### Target Users

1. **Developers** — Building iOS/Android/Web apps; need real-time a11y feedback during development
2. **QA/Accessibility Specialists** — Running compliance audits before release; require detailed reports
3. **Platform Teams** — Governance role; must block PRs with critical violations or regressions
4. **Design Systems Teams** — Ensuring all components meet AA standards

## Key Features

| Feature | Details |
|---------|---------|
| **Multi-platform auditing** | iOS (Swift/SwiftUI), Android (Kotlin/XML), Web (React/HTML/CSS) |
| **WCAG 2.1 AA coverage** | 25 conformance criteria (1.1.1–4.1.2); severity: critical/serious/moderate/minor |
| **Iterative refinement** | Planner → Scanner → Evaluator → Compliance Check → Targeted Re-scan (max 3 iterations) |
| **Human-in-the-loop** | User approves audit scope before scanning begins; can approve/reject violations interactively |
| **Structured findings** | Pydantic models with IDs, WCAG citations, file paths, line numbers, fix suggestions |
| **Scoring & PR blocking** | Score 0–100; blocks PR on: any critical, ≥5 serious, or regression flag |
| **Web dashboard** | React + Vite frontend; real-time SSE streaming; chat interface with agent activity timeline |

## Non-Goals

- **Mobile app building** — Not a dev tool for writing code; focused on auditing existing codebases
- **Training & education** — Not a learning platform; assumes users understand WCAG basics
- **Accessibility fixes** — Does not modify code; only provides recommendations and fix templates
- **Full WCAG conformance** — Targets AA level; WCAG AAA conformance out of scope
- **Custom WCAG criteria** — Uses standardized 25 AA criteria; no user-defined rules

## Architecture Highlights

- **ADK-based agent graph** — 6-agent pipeline (scope_analyzer → platform_detector → a11y_scanner → a11y_evaluator → compliance_checker → audit_report_composer)
- **Session-based state** — Inter-agent communication via `output_key` (immutable session state)
- **Callbacks for scoring** — `collect_findings_callback` deduplicates, `build_report_callback` computes scores
- **Structured output schemas** — Pydantic models force agents to emit valid JSON
- **Tool-centric design** — 3 FunctionTools: `search_codebase`, `read_file_content`, `list_files`

## Success Metrics

- **Audit quality** — No false negatives for critical violations (WCAG 1.1.1, 2.1.1, 3.3.1)
- **Time to audit** — Full multi-platform scan completes in < 2 minutes
- **User satisfaction** — ≥90% of findings actionable; < 5% false positives
- **Compliance coverage** — Detects ≥95% of violations in test suites
- **Iteration efficiency** — Max 3 refinement passes; early exit on compliance

## Compliance & Security

- **Data handling** — Scans local codebase only; no data sent beyond Gemini API
- **Model trust** — Evaluator and compiler models are `gemini-2.5-pro` (no downgrade without config change)
- **GDPR compliance** — No user data stored; all context discarded after session ends
- **Secrets safety** — Agents may encounter API keys in code; no explicit masking (user responsible for `.env` patterns)

## Business Model

- **Pricing** — TBD (currently internal tool)
- **Deployment** — Self-hosted Python backend + React frontend; requires Google Cloud Project or `GOOGLE_API_KEY`
- **SLA** — None (open-source community version)

## Dependencies

- **google-adk ≥1.8.0** — Agent framework
- **pydantic ≥2.0.0** — Data validation
- **Gemini API** — LLM backbone
- **React 19, Vite 6, Tailwind CSS v4** — Frontend stack

## Future Roadmap

1. **Fix templates** — Auto-apply common remediations (e.g., add `accessibilityLabel` to iOS buttons)
2. **CI/CD integration** — GitHub Actions workflows; automated PR checks
3. **Multi-repo audits** — Audit monorepos with dependency graphs
4. **Diff-mode auditing** — Scan only changed files (git diff-based)
5. **Custom criteria** — Allow teams to define org-specific WCAG extensions
6. **Regression tracking** — Historical violation database; detect new regressions vs. old findings
