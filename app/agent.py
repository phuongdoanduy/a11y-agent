# Copyright 2026 Optimus Team
# MIT License
#
# epost-a11y-agent: Multi-platform WCAG 2.1 AA auditor
# Architecture: Google ADK (Agent Development Kit)
# Pattern: Planner → Scanner → Iterative Refinement → Report Composer
# Inspired by: google/adk-samples/python/agents/deep-search

import datetime
import json
import logging
from collections.abc import AsyncGenerator
from typing import Literal

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.apps.app import App
from google.adk.events import Event, EventActions
from google.adk.planners import BuiltInPlanner
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from .config import config


# ═══════════════════════════════════════════════════════════════
# Structured Output Models
# ═══════════════════════════════════════════════════════════════

class A11yViolation(BaseModel):
    """A single accessibility violation found during audit."""
    id: str = Field(description="Unique finding ID, e.g. 'a11y-001'")
    wcag_criterion: str = Field(description="WCAG 2.1 success criterion, e.g. '1.1.1'")
    severity: Literal["critical", "serious", "moderate", "minor"] = Field(
        description="Violation severity level"
    )
    title: str = Field(description="Short descriptive title of the violation")
    file_path: str = Field(description="File path where violation was found")
    line_number: int | None = Field(default=None, description="Line number if identifiable")
    description: str = Field(description="Detailed description of the issue")
    code_snippet: str = Field(default="", description="Relevant code snippet")
    fix_suggestion: str = Field(description="Suggested fix or remediation")
    fix_template: str = Field(default="other_manual", description="Fix template ID to apply")
    platform: Literal["ios", "android", "web", "cross-platform"] = Field(
        description="Platform where violation was found"
    )
    regression: bool = Field(
        default=False,
        description="True if this was previously resolved and has reappeared"
    )


class AuditResult(BaseModel):
    """Complete audit output from a single platform scan."""
    platform: str = Field(description="Platform audited (ios/android/web)")
    total_violations: int = Field(description="Total number of violations found")
    critical_count: int = Field(default=0)
    serious_count: int = Field(default=0)
    moderate_count: int = Field(default=0)
    minor_count: int = Field(default=0)
    score: int = Field(description="Accessibility score 0-100")
    block_pr: bool = Field(description="Whether PR should be blocked")
    violations: list[A11yViolation] = Field(default_factory=list)
    wcag_criteria_checked: list[str] = Field(default_factory=list)
    files_scanned: int = Field(default=0)


class A11yFeedback(BaseModel):
    """Evaluation feedback on audit quality — used by the evaluator agent."""
    grade: Literal["pass", "fail"] = Field(
        description="'pass' if audit is thorough enough, 'fail' if needs more scanning"
    )
    comment: str = Field(description="Detailed evaluation of audit quality")
    gaps: list[str] = Field(
        default_factory=list,
        description="Specific gaps found in coverage (WCAG criteria not checked, files missed, etc.)"
    )
    follow_up_scans: list[str] = Field(
        default_factory=list,
        description="Specific areas/patterns to re-scan (file globs, WCAG criteria, component names)"
    )


# ═══════════════════════════════════════════════════════════════
# Tools — Codebase Scanning Functions
# ═══════════════════════════════════════════════════════════════

def search_codebase(pattern: str, file_glob: str = "*", root_dir: str = ".") -> str:
    """Search codebase for accessibility-related patterns.

    Args:
        pattern: Regex pattern to search for in file contents.
        file_glob: File glob filter (e.g. "*.swift", "*.kt", "*.tsx").
        root_dir: Absolute path to the project root to scan. Defaults to CWD.

    Returns:
        JSON string with matching files, line numbers, and content.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include", file_glob, "-E", pattern, "."],
            capture_output=True, text=True, timeout=30,
            cwd=root_dir,
        )
        matches = []
        for line in result.stdout.strip().split("\n")[:50]:  # Cap at 50
            if not line:
                continue
            parts = line.split(":", 2)
            if len(parts) >= 3:
                matches.append({
                    "file": parts[0],
                    "line": int(parts[1]) if parts[1].isdigit() else 0,
                    "content": parts[2].strip()[:200],
                })
        return json.dumps({"matches": matches, "count": len(matches)})
    except Exception as e:
        return json.dumps({"error": str(e), "matches": [], "count": 0})


def read_file_content(file_path: str, start_line: int = 1, end_line: int = 50) -> str:
    """Read a specific range of lines from a file.

    Args:
        file_path: Path to the file.
        start_line: Starting line number (1-indexed).
        end_line: Ending line number (inclusive).

    Returns:
        File content with line numbers.
    """
    try:
        with open(file_path) as f:
            lines = f.readlines()
        selected = lines[start_line - 1:end_line]
        return "\n".join(
            f"{start_line + i}| {line.rstrip()}"
            for i, line in enumerate(selected)
        )
    except Exception as e:
        return f"Error reading {file_path}: {e}"


def list_files(glob_pattern: str, root_dir: str = ".") -> str:
    """List files matching a glob pattern.

    Args:
        glob_pattern: Glob pattern (e.g. "**/*.swift", "**/*.tsx")
        root_dir: Absolute path to the project root to glob from. Defaults to CWD.

    Returns:
        JSON list of matching file paths.
    """
    from pathlib import Path
    try:
        files = [str(p) for p in Path(root_dir).glob(glob_pattern) if p.is_file()]
        return json.dumps({"files": files[:100], "count": len(files)})
    except Exception as e:
        return json.dumps({"error": str(e), "files": [], "count": 0})


# Wrap as ADK FunctionTools
codebase_search_tool = FunctionTool(search_codebase)
file_reader_tool = FunctionTool(read_file_content)
file_lister_tool = FunctionTool(list_files)


# ═══════════════════════════════════════════════════════════════
# Callbacks — Side Effects
# ═══════════════════════════════════════════════════════════════

def collect_findings_callback(callback_context: CallbackContext) -> None:
    """Collects and deduplicates a11y findings from scan results.

    Processes session events to extract violations found by scanner agents,
    builds a cumulative findings database with deduplication by (file, wcag, title).
    """
    session = callback_context._invocation_context.session
    findings = callback_context.state.get("all_findings", [])
    seen_keys = {(f["file_path"], f.get("wcag_criterion", ""), f["title"]) for f in findings}

    scan_result = callback_context.state.get("audit_scan_result", "")
    if not scan_result:
        return

    try:
        if isinstance(scan_result, str):
            data = json.loads(scan_result)
        else:
            data = scan_result

        violations = data.get("violations", [])
        for v in violations:
            if isinstance(v, dict):
                key = (v.get("file_path", ""), v.get("wcag_criterion", ""), v.get("title", ""))
                if key not in seen_keys:
                    findings.append(v)
                    seen_keys.add(key)
    except (json.JSONDecodeError, TypeError):
        pass

    callback_context.state["all_findings"] = findings


def build_report_callback(callback_context: CallbackContext) -> genai_types.Content:
    """Post-processes the final audit report, adding summary statistics.

    Computes aggregate scores, determines PR blocking, and formats
    the final markdown report with severity breakdown.
    """
    report = callback_context.state.get("final_audit_report", "")
    findings = callback_context.state.get("all_findings", [])
    platform = callback_context.state.get("audit_platform", "unknown")

    # Compute summary
    severity_counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for f in findings:
        sev = f.get("severity", "minor")
        if sev in severity_counts:
            severity_counts[sev] += 1

    total = len(findings)
    score = 100
    for f in findings:
        sev = f.get("severity", "minor")
        score += config.severity_scores.get(sev, -1)
    score = max(0, min(100, score))

    block_pr = (
        (config.block_on_critical and severity_counts["critical"] > 0)
        or (config.block_on_serious_count > 0
            and severity_counts["serious"] >= config.block_on_serious_count)
        or any(f.get("regression") for f in findings)
    )

    summary = {
        "platform": platform,
        "total_violations": total,
        "score": score,
        "block_pr": block_pr,
        "severity_breakdown": severity_counts,
        "compliance_threshold": config.compliance_threshold,
        "pass": score >= config.compliance_threshold and not block_pr,
    }

    callback_context.state["audit_summary"] = summary

    # Inject summary header into report
    header = f"""## A11y Audit Summary — {platform.upper()}

| Metric | Value |
|--------|-------|
| Score | **{score}/100** |
| Total Violations | {total} |
| Critical | {severity_counts['critical']} |
| Serious | {severity_counts['serious']} |
| Moderate | {severity_counts['moderate']} |
| Minor | {severity_counts['minor']} |
| Block PR | {'🚫 YES' if block_pr else '✅ NO'} |
| Compliance | {'PASS' if summary['pass'] else 'FAIL'} |

---

"""
    final_report = header + report
    callback_context.state["final_report_with_summary"] = final_report
    return genai_types.Content(parts=[genai_types.Part(text=final_report)])


# ═══════════════════════════════════════════════════════════════
# Eval-compatible wrappers (ADK eval requires instruction: str on all agents)
# ═══════════════════════════════════════════════════════════════

class _EvalSequentialAgent(SequentialAgent):
    instruction: str = ""
    tools: list = []


class _EvalLoopAgent(LoopAgent):
    instruction: str = ""
    tools: list = []


# ═══════════════════════════════════════════════════════════════
# Custom Agent for Loop Control
# ═══════════════════════════════════════════════════════════════

class ComplianceChecker(BaseAgent):
    """Checks audit evaluation and escalates to stop loop if compliance is met.

    Analogous to EscalationChecker in deep-search — breaks the iterative
    refinement loop when the evaluator grades the audit as 'pass'.
    """

    instruction: str = ""
    tools: list = []

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        evaluation = ctx.session.state.get("audit_evaluation")
        if evaluation and evaluation.get("grade") == "pass":
            logging.info(
                f"[{self.name}] Audit evaluation passed. "
                f"Escalating to stop refinement loop."
            )
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            logging.info(
                f"[{self.name}] Audit evaluation failed or not found. "
                f"Continuing refinement loop."
            )
            yield Event(author=self.name)


# ═══════════════════════════════════════════════════════════════
# AGENT DEFINITIONS
# ═══════════════════════════════════════════════════════════════

# ── 1. Scope Analyzer (analogous to plan_generator) ──────────
scope_analyzer = LlmAgent(
    model=config.worker_model,
    name="scope_analyzer",
    description=(
        "Analyzes the audit request, determines scope (files, platform, "
        "WCAG criteria), and creates a targeted audit plan."
    ),
    instruction=f"""You are an accessibility audit strategist. Your job is to
create a focused A11Y AUDIT PLAN based on the user's request.

CURRENT AUDIT REQUEST:
{{{{audit_request?}}}}

EXISTING KNOWN FINDINGS:
{{{{known_findings?}}}}

PROJECT ROOT DIRECTORY: {{{{target_dir?}}}} (use as root_dir in all tool calls; defaults to "." if not set)

**YOUR OUTPUT MUST BE a structured audit plan with:**

1. **Platform Detection**: ios / android / web / cross-platform
2. **Scope**: Which files/directories to scan (glob patterns)
3. **WCAG Criteria**: Which of the {len(config.wcag_aa_criteria)} AA criteria are relevant
4. **Priority Areas**: High-risk areas (forms, images, focus management, etc.)
5. **Known Findings Check**: Patterns from prior violations to re-verify

**RULES:**
- Be specific about file patterns (e.g. "**/*.swift", "**/*.tsx")
- ALWAYS pass root_dir from "target_dir" session state to list_files and search_codebase
- Map file types to WCAG criteria automatically:
  - Images → 1.1.1 (Non-text Content)
  - Forms/inputs → 3.3.1, 3.3.2, 1.3.1
  - Focus/navigation → 2.4.3, 2.4.7, 2.1.1
  - Colors/contrast → 1.4.1, 1.4.3
  - Headings → 1.3.1, 2.4.6
- If known findings exist, include regression checks for resolved items
- Keep the plan actionable and scoped — audit what matters, not everything

Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
""",
    tools=[codebase_search_tool, file_lister_tool],
)


# ── 2. Platform Detector (analogous to section_planner) ──────
platform_detector = LlmAgent(
    model=config.worker_model,
    name="platform_detector",
    description=(
        "Detects platform from files, loads appropriate a11y ruleset, "
        "and creates a checklist of WCAG criteria to verify."
    ),
    instruction="""You are a platform detection specialist. Given the audit plan,
identify the target platform and create a structured audit checklist.

**Platform Detection Rules:**
- `.swift`, `.xib`, `.storyboard`, SwiftUI → **iOS** (VoiceOver, UIKit, SwiftUI)
- `.kt`, `.kts`, Compose, XML layouts → **Android** (TalkBack, Compose, Views)
- `.tsx`, `.jsx`, `.html`, `.css`, ARIA → **Web** (Screen readers, keyboard, ARIA)
- Mixed → **cross-platform** (run all applicable checklists)

**Your output must include:**
1. Platform: ios / android / web / cross-platform
2. Checklist: WCAG criteria to verify (from the audit plan)
3. Platform-specific patterns to scan for:
   - iOS: accessibilityLabel, accessibilityTraits, isAccessibilityElement, .header, accessibilityHint
   - Android: contentDescription, Modifier.semantics{}, heading(), mergeDescendants, onClickLabel
   - Web: aria-label, role, tabIndex, :focus-visible, alt, <label>, heading hierarchy
4. File glob patterns for the scanner

Output as structured JSON.
""",
    output_key="audit_checklist",
)


# ── 3. A11y Scanner (analogous to section_researcher) ────────
a11y_scanner = LlmAgent(
    model=config.worker_model,
    name="a11y_scanner",
    description=(
        "Scans the codebase for WCAG violations using grep/read tools, "
        "applies platform-specific rules, and produces structured findings."
    ),
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction=f"""You are a meticulous accessibility auditor. Execute the
audit checklist from 'audit_checklist' state key with absolute thoroughness.

PROJECT ROOT: {{{{target_dir?}}}} — pass this as root_dir in ALL list_files and search_codebase calls.

**EXECUTION PHASES:**

**Phase 1: File Discovery**
- Use `list_files(glob_pattern, root_dir=target_dir)` to enumerate files matching the glob patterns
- Count total files to scan

**Phase 2: Pattern Scanning**
- Use `search_codebase(pattern, file_glob, root_dir=target_dir)` to find accessibility-related patterns
- Scan for MISSING patterns (e.g., images without alt, buttons without labels)
- Scan for INCORRECT patterns (e.g., tabIndex > 0, aria-label="")

**Phase 3: Deep Inspection**
- Use `read_file_content` to examine suspicious files in detail
- Verify context around flagged patterns
- Check for fix templates that apply

**Phase 4: Finding Classification**
For each violation found, classify:
- WCAG criterion (e.g., "1.1.1")
- Severity: critical (-10pts), serious (-5pts), moderate (-2pts), minor (-1pt)
- Platform: ios / android / web
- Fix template: add_alt_text, add_aria_label, add_heading_level, etc.
- Whether this is a regression of a known finding

**CRITICAL RULES:**
- Be THOROUGH — scan every file in scope
- Be SPECIFIC — file:line for every finding
- Be ACTIONABLE — every finding needs a fix suggestion
- Score starts at 100, subtract per finding severity
- ALWAYS pass root_dir when calling list_files and search_codebase

Output a structured audit result as JSON with:
total_violations, score, block_pr, violations[], wcag_criteria_checked, files_scanned
""",
    tools=[codebase_search_tool, file_reader_tool, file_lister_tool],
    output_key="audit_scan_result",
    after_agent_callback=collect_findings_callback,
)


# ── 4. A11y Evaluator (analogous to research_evaluator) ─────
a11y_evaluator = LlmAgent(
    model=config.critic_model,
    name="a11y_evaluator",
    description=(
        "Critically evaluates audit thoroughness. Grades pass/fail "
        "and identifies coverage gaps for targeted follow-up scans."
    ),
    instruction=f"""You are a meticulous quality assurance analyst evaluating
the accessibility audit in 'audit_scan_result'.

**CRITICAL RULES:**
1. Your ONLY job is to assess audit COMPLETENESS and QUALITY.
2. Do NOT re-audit the code — evaluate the audit process itself.
3. Check against the WCAG AA criteria list: {config.wcag_aa_criteria}

**EVALUATION CRITERIA:**
- Coverage: Were all files in scope scanned?
- Depth: Were WCAG criteria thoroughly checked?
- Specificity: Are findings specific (file:line, not vague)?
- Actionability: Do findings have clear fix suggestions?
- Score validity: Does the score calculation seem correct?

**Be CRITICAL.** If you find significant gaps:
- Grade "fail"
- List specific gaps (which WCAG criteria missed, which files unscanned)
- Provide follow-up scan targets (file patterns, WCAG criteria, component names)

If audit is thorough, grade "pass".

Your response must be a single JSON object matching the A11yFeedback schema.
""",
    output_schema=A11yFeedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="audit_evaluation",
)


# ── 5. Targeted Scanner (analogous to enhanced_search_executor) ─
targeted_scanner = LlmAgent(
    model=config.worker_model,
    name="targeted_scanner",
    description=(
        "Executes targeted follow-up scans based on evaluator feedback. "
        "Focuses on specific gaps, missed files, and unverified WCAG criteria."
    ),
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""You are a specialist accessibility auditor executing a
targeted refinement pass. You have been activated because the previous
audit was graded as 'fail' by the evaluator.

PROJECT ROOT: {target_dir?} — pass this as root_dir in ALL list_files and search_codebase calls.

1. Review 'audit_evaluation' state key to understand the feedback and gaps.
2. For EACH gap listed:
   - Use `search_codebase(pattern, file_glob, root_dir=target_dir)` with specific patterns
   - Use `read_file_content` to inspect suspicious files
   - Check the WCAG criteria that were missed
3. MERGE new findings with existing findings in 'audit_scan_result'.
4. Your output MUST be the complete, improved audit result with all violations.
5. Recalculate the score after adding new findings.
6. ALWAYS pass root_dir when calling list_files and search_codebase.
""",
    tools=[codebase_search_tool, file_reader_tool, file_lister_tool],
    output_key="audit_scan_result",
    after_agent_callback=collect_findings_callback,
)


# ── 6. Audit Report Composer (analogous to report_composer) ──
audit_report_composer = LlmAgent(
    model=config.critic_model,
    name="audit_report_composer",
    include_contents="none",
    description=(
        "Transforms audit findings into a professional, actionable "
        "accessibility audit report with fix suggestions and priority ranking."
    ),
    instruction="""Transform the audit data into a polished, professional
accessibility audit report.

---

### INPUT DATA
* Audit Checklist: `{audit_checklist}`
* Scan Results: `{audit_scan_result}`
* Known Findings: `{known_findings?}`

---

### REPORT STRUCTURE

## 1. Executive Summary
- Platform audited
- Overall score and compliance status
- PR blocking decision with rationale

## 2. Violations by Severity
For each severity level (critical → minor):
- Finding ID, WCAG criterion, title
- File:line reference
- Description of issue
- Code snippet (if available)
- Suggested fix with code example

## 3. WCAG Coverage Matrix
Table showing which AA criteria were checked and pass/fail status.

## 4. Regression Analysis
- Any previously resolved findings that reappeared
- New findings vs known findings

## 5. Remediation Priority
Ordered list of fixes by impact (critical first, then serious, etc.)

## 6. Fix Templates
For each unique fix_template used, provide the platform-specific code pattern.

---

### RULES
- Every finding MUST have: file path, WCAG criterion, severity, fix suggestion
- Use code snippets from the scan results — do not fabricate code
- Group by severity, then by WCAG criterion within each severity
- Include the compliance threshold and whether the audit passes or fails
""",
    output_key="final_audit_report",
    after_agent_callback=build_report_callback,
)


# ═══════════════════════════════════════════════════════════════
# ORCHESTRATION PIPELINE
# ═══════════════════════════════════════════════════════════════

# The iterative refinement loop (analogous to iterative_refinement_loop)
a11y_refinement_loop = _EvalLoopAgent(
    name="a11y_refinement_loop",
    max_iterations=config.max_audit_iterations,
    sub_agents=[
        a11y_evaluator,
        ComplianceChecker(name="compliance_checker"),
        targeted_scanner,
    ],
)

# The main audit pipeline (analogous to research_pipeline)
a11y_audit_pipeline = _EvalSequentialAgent(
    name="a11y_audit_pipeline",
    description=(
        "Executes a pre-scoped accessibility audit. Performs iterative "
        "scanning, evaluation, and composes a final WCAG 2.1 AA report."
    ),
    sub_agents=[
        platform_detector,
        a11y_scanner,
        a11y_refinement_loop,
        audit_report_composer,
    ],
)

# The interactive planner (analogous to interactive_planner_agent)
interactive_audit_planner = LlmAgent(
    name="interactive_audit_planner",
    model=config.worker_model,
    description=(
        "The primary a11y audit assistant. Collaborates with the user to "
        "define audit scope, then executes the full audit pipeline upon approval."
    ),
    instruction=f"""You are an accessibility audit planning assistant.
Your primary function is to convert ANY a11y request into a structured audit plan.

**TARGET DIRECTORY EXTRACTION (check this first):**
If the user's message starts with "[TARGET_DIR: <path>]", extract <path> as the
project root directory. Store it in session state key "target_dir". Strip the
"[TARGET_DIR: ...]" prefix before treating the rest as the audit request.
All tool calls that accept root_dir MUST pass root_dir=<path>.
If no [TARGET_DIR: ...] prefix is present, use root_dir="." (current directory).

**CRITICAL RULES:**
1. Never audit code directly. Your job is to PLAN, then DELEGATE.
2. Use `scope_analyzer` tool to create an audit plan for the user's request.
3. Present the plan clearly: platform, scope (files), WCAG criteria, priority areas.
4. Incorporate user feedback until the plan is approved.
5. Once user gives EXPLICIT approval, delegate to `a11y_audit_pipeline`.

**WORKFLOW:**
1. **Plan**: Use scope_analyzer → present audit plan
2. **Refine**: Incorporate feedback → update plan
3. **Execute**: User approves → delegate to a11y_audit_pipeline
4. **Report**: Pipeline returns → present findings to user

Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
Do not perform any scanning yourself. Plan → Refine → Delegate.
""",
    sub_agents=[a11y_audit_pipeline],
    tools=[AgentTool(scope_analyzer)],
    output_key="audit_plan",
)


# ═══════════════════════════════════════════════════════════════
# ROOT AGENT & APP
# ═══════════════════════════════════════════════════════════════

root_agent = interactive_audit_planner
app = App(root_agent=root_agent, name="app")
