# Project Roadmap — epost-a11y-agent

## Current State (MVP Complete)

**Status:** v0.1.0 — Multi-platform accessibility audit agent with human-in-the-loop refinement loop

**Completed Features:**
- ✅ ADK-based agent graph (6-agent pipeline: scope → detect → scan → evaluate → refine → report)
- ✅ WCAG 2.1 AA coverage (25 criteria: 1.1.1–4.1.2)
- ✅ Multi-platform support (iOS, Android, Web detection)
- ✅ Iterative refinement loop (max 3 iterations; early exit on compliance)
- ✅ Scoring algorithm (0–100 score; PR blocking on critical/serious/regression)
- ✅ React + Vite frontend with SSE streaming
- ✅ Pydantic models for structured findings
- ✅ Configuration singleton with auth auto-selection (API key vs. Vertex AI)

**Test Coverage:** None (manual testing only; unit tests needed)

**Known Limitations:**
- Agent detection heuristic-based (keyword matching in streamed text)
- No regression tracking database (findings not persisted)
- No fix templates or auto-remediation
- No CI/CD integration
- Single-repo audits only (no monorepo support)
- No custom WCAG criteria support

---

## Phase 1: Stabilization & Testing (2 weeks)

**Goal:** Production-ready MVP with test coverage and documentation

### Tasks

- [ ] **Unit tests for scoring algorithm**
  - Test compute_score() with various violation combinations
  - Test should_block_pr() logic against all block conditions
  - Test edge cases: no violations, all critical, regressions
  - Expected: ≥95% coverage on scoring module

- [ ] **ADK agent graph integration tests**
  - Mock Gemini API responses
  - Test LoopAgent early exit on compliance pass
  - Test callback deduplication logic
  - Test output_key state flow through pipeline
  - Expected: 3–5 end-to-end test scenarios

- [ ] **Frontend component unit tests (Vitest)**
  - Test AuditDashboard scoring display
  - Test FindingsList filtering by severity
  - Test WCAGMatrix color coding
  - Expected: ≥80% component coverage

- [ ] **API integration tests**
  - Test session creation endpoint
  - Test SSE streaming and JSON parsing
  - Test error handling on malformed input
  - Expected: Happy path + 3 error scenarios

- [ ] **Documentation**
  - Update README with API endpoint reference
  - Add troubleshooting guide
  - Document configuration options
  - Expected: README ≥500 LOC, troubleshooting ≥200 LOC

---

## Phase 2: Fix Templates & Auto-Remediation (3 weeks)

**Goal:** Developers can apply suggested fixes with one click; reduce manual remediation time

### Deliverables

- [ ] **Fix template registry**
  - Create `app/fix_templates/` with platform-specific remediation snippets
  - Templates: add accessibilityLabel (iOS), contentDescription (Android), aria-label (Web)
  - Template format: Jinja2 with variables (element_id, attribute_name, etc.)
  - Expected: ≥15 templates covering 80% of critical violations

- [ ] **Fix application API**
  - `POST /api/sessions/{id}/apply-fix` endpoint
  - Validates template against codebase
  - Generates patch file (unified diff)
  - Returns: patch content + application status
  - Expected: Support iOS, Android, Web codebases

- [ ] **Frontend fix UI**
  - "Apply Fix" button on each violation in FindingsList
  - Modal showing diff preview before apply
  - Success message on successful patch generation
  - Expected: UX tested with designers

- [ ] **Template validation**
  - Test fix templates against real codebase samples
  - Ensure generated fixes are valid syntax
  - Expected: 100% of templates pass validation

---

## Phase 3: CI/CD Integration (2 weeks)

**Goal:** Integrate epost-a11y-agent into GitHub Actions; block PRs on violations

### Deliverables

- [ ] **GitHub Actions workflow template**
  - File: `.github/workflows/a11y-audit.yml`
  - Triggers on: pull_request, push to main
  - Runs epost-a11y-agent on changed files
  - Posts findings as PR comment
  - Blocks merge if critical violations found
  - Expected: Works with public + private repos

- [ ] **Diff-mode auditing**
  - `--diff-base` flag to audit only changed files
  - `git diff main...branch | audit --diff-mode`
  - Significantly faster than full audit
  - Expected: 10x speedup for incremental PRs

- [ ] **PR comment reporter**
  - Generates GitHub markdown comment with findings
  - Summary table: severity counts, score, block status
  - Details section: file paths, line numbers, fix suggestions
  - Expected: Comment ≤64KB (GH limit)

- [ ] **Status check integration**
  - Creates GitHub check run: "Accessibility Audit"
  - Check passes if score ≥ compliance_threshold
  - Check fails if critical violations or regressions
  - Expected: Blocks merge on failure

---

## Phase 4: Multi-Repo Auditing (2 weeks)

**Goal:** Support auditing monorepos with dependency graphs; cross-repo impact analysis

### Deliverables

- [ ] **Workspace manifest parsing**
  - Detect package.json workspaces, Gradle multi-module, Swift package structure
  - Build dependency graph (which package depends on what)
  - Expected: Support npm, yarn, Gradle, SPM

- [ ] **Cascading audit**
  - Audit root package + all dependents when violation found
  - Identify which teams are affected by regression
  - Expected: Reduce false negatives in monorepos

- [ ] **Per-workspace configuration**
  - `.a11y-config.yaml` at each workspace root
  - Override compliance_threshold, block_on_serious_count per workspace
  - Expected: Teams can enforce stricter standards

- [ ] **Aggregate report**
  - Combine findings from all workspaces
  - Group by workspace, platform, severity
  - Expected: Single report covering entire monorepo

---

## Phase 5: Regression Tracking & Historical Analysis (3 weeks)

**Goal:** Detect regressions automatically; track compliance trends over time

### Deliverables

- [ ] **Violation database**
  - PostgreSQL table: `violations` (id, session_id, wcag_criterion, file_path, line_number, hash, created_at, resolved_at)
  - Index on: (hash, created_at) for deduplication + historical lookup
  - Expected: Supports ≥1M violation records

- [ ] **Regression detection algorithm**
  - Hash violations by (wcag_criterion, file_path, line_number)
  - Compare current audit against last 5 audits
  - Flag as regression if: found now, resolved in past 30 days
  - Expected: <1% false positive regression flagging

- [ ] **Historical API**
  - `GET /api/sessions/{id}/history?days=30` — violations over time
  - `GET /api/violations/{hash}/timeline` — single violation history
  - Expected: JSON response with time-series data

- [ ] **Trend dashboard**
  - React component showing compliance trend (30-day graph)
  - Regression analysis: top regressors, most frequently fixed violations
  - Expected: Helps prioritize team training

- [ ] **Database migrations**
  - Versioned migrations in `app/migrations/` using Alembic
  - Expected: Zero-downtime schema updates

---

## Phase 6: Custom WCAG Criteria & Org Extensions (2 weeks)

**Goal:** Enterprises can define org-specific accessibility rules

### Deliverables

- [ ] **Criteria registry (pluggable)**
  - YAML file: `org-criteria.yaml` defining custom WCAG extensions
  - Format: criterion_id, description, platforms, severity, checker_prompt
  - Expected: Support ≥20 custom criteria per org

- [ ] **Dynamic prompt injection**
  - Scanner agent receives org criteria at runtime
  - Evaluator grades against combined standard + custom criteria
  - Expected: Custom criteria treated equally to WCAG AA

- [ ] **Org admin API**
  - `POST /api/orgs/{id}/criteria` — create custom criterion
  - `PUT /api/orgs/{id}/criteria/{id}` — update
  - `DELETE /api/orgs/{id}/criteria/{id}` — remove
  - Expected: CRUD + validation

- [ ] **Org config API**
  - Per-org settings: compliance_threshold, severity_scores, block_on_serious_count
  - Expected: Override global config per organization

---

## Phase 7: Performance & Scaling (2 weeks, concurrent with Phase 6)

**Goal:** Handle enterprise workloads; optimize latency and cost

### Deliverables

- [ ] **Caching layer**
  - Cache scan results by (platform, file_hash) for 24 hours
  - Skip full audit if codebase unchanged since last audit
  - Expected: 80% cache hit rate on typical monorepos

- [ ] **Parallel auditing**
  - Split large monorepos across multiple agent sessions
  - Merge results at end (deduplication + score aggregation)
  - Expected: 2x speedup for codebases ≥10K files

- [ ] **Model switching**
  - Allow switching worker_model to cheaper model (e.g., Gemini 1.5)
  - Trade: slightly lower accuracy for 10x cost reduction
  - Expected: Configurable per org

- [ ] **Token budget optimization**
  - Implement adaptive refinement loop (reduce iterations if budget low)
  - Compress chat history before feeding to evaluator
  - Expected: Reduce cost per audit by 30%

- [ ] **Load testing**
  - Simulate 100 concurrent sessions
  - Measure latency p50, p95, p99
  - Expected: p95 latency < 30s for typical audit

---

## Phase 8: Accessibility Audit of epost-a11y-agent (1 week)

**Goal:** Practice what we preach; ensure UI is WCAG 2.1 AA compliant

### Deliverables

- [ ] **Self-audit**
  - Run epost-a11y-agent on frontend codebase
  - Fix all findings (UI contrast, keyboard nav, screen reader labels)
  - Expected: Score ≥95, zero critical violations

- [ ] **Automated UI tests**
  - Axe accessibility scanner in Playwright tests
  - CI check ensures regressions caught
  - Expected: 100% pass rate

---

## Backlog (Future Consideration)

- **Mobile app** — Native iOS/Android client for on-device auditing
- **IDE plugins** — VSCode, Android Studio, Xcode extensions for real-time linting
- **WCAG AAA support** — Extended set of criteria beyond AA
- **Automated fix application** — Apply templates directly to codebase (with review)
- **Diff-aware reporting** — Show before/after for violations fixed between audits
- **Team collaboration** — Shared audit sessions, comments on findings, assignment tracking
- **SLA monitoring** — Alert teams when violations age beyond threshold
- **ML-powered filtering** — Learn which findings are false positives; suppress them

---

## Success Metrics

| Phase | Metric | Target | Notes |
|-------|--------|--------|-------|
| 1 | Test coverage | ≥85% | Scoring + agent graph |
| 2 | Fix template coverage | ≥80% | Critical violations addressable |
| 3 | CI integration time | <5 min | Per PR audit runtime |
| 4 | Monorepo scaling | <1 sec per changed file | Linear complexity |
| 5 | Regression detection accuracy | >99% | Minimize false positives |
| 6 | Custom criteria adoption | ≥5 per org | Measure post-launch |
| 7 | Cost per audit | <$0.50 | Gemini API pricing |
| 8 | UI accessibility score | ≥95 | Self-compliance |

---

## Timeline Summary

```
Week 1-2:   Phase 1 (Stabilization & Testing)
Week 3-5:   Phase 2 (Fix Templates)
Week 6-7:   Phase 3 (CI/CD Integration)
Week 8-9:   Phase 4 (Multi-Repo Auditing)
Week 10-12: Phase 5 (Regression Tracking) + Phase 7 (Perf) in parallel
Week 13-14: Phase 6 (Custom Criteria) + Phase 7 cont.
Week 15:    Phase 8 (Self-Audit)
```

**Estimated Total:** 15 weeks to full feature completeness. MVP (Phase 1) production-ready in 2 weeks.
