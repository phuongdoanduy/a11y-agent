---
phase: 4
title: "Eval Verification"
status: pending
priority: P1
effort: "20m"
dependencies: [1, 2, 3]
---

# Phase 4: Eval Verification

## Overview

Re-run the full-pipeline eval after all three fixes and compare against the baseline results from
`results_20260606_135100.json`. All four metrics must show improvement; `tool_use_quality` and
`final_response_quality` must move off zero.

## Requirements

- Functional: `agents-cli eval run` completes without errors on `full-pipeline-dataset.json`.
- Functional: `multi_turn_tool_use_quality` mean score > 0 (was 0.000).
- Functional: `final_response_quality` mean score > 0 (was 0.000).
- Functional: `multi_turn_task_success` mean score > 0.267 (was 0.267 baseline).
- Functional: `custom_audit_plan_quality` mean score >= 4.5 (must not regress from baseline).
- Non-functional: No regressions introduced — run `agents-cli eval compare` to confirm.

## Baseline (reference)

From `artifacts/grade_results/results_20260606_135100.json`:

| Metric | Baseline mean | Target |
|--------|--------------|--------|
| `multi_turn_task_success_v1` | 0.267 | > 0.267 |
| `multi_turn_tool_use_quality_v1` | 0.000 | > 0.000 |
| `final_response_quality_v1` | 0.000 | > 0.000 |
| `custom_audit_plan_quality` | 4.500 | >= 4.500 |

## Related Code Files

- Read: `artifacts/grade_results/results_20260606_135100.json` (baseline)
- Read: `artifacts/grade_results/results_<new_ts>.json` (new run)

## Implementation Steps

1. Validate the dataset JSON is well-formed before running inference:
   ```bash
   python3 -m json.tool tests/eval/datasets/full-pipeline-dataset.json > /dev/null && echo "OK"
   ```

2. Re-run the full eval (generate + grade) with the same config as the baseline:
   ```bash
   agents-cli eval run \
     --dataset tests/eval/datasets/full-pipeline-dataset.json \
     --config tests/eval/eval_config.yaml
   ```
   Note the new results filename printed at the end (e.g. `results_20260606_HHMMSS.json`).

3. Compare new results against the baseline:
   ```bash
   agents-cli eval compare \
     artifacts/grade_results/results_20260606_135100.json \
     artifacts/grade_results/results_<new_ts>.json
   ```

4. Check per-case rubric verdicts in the new results JSON to confirm `scope_analyzer` is now
   found in the trace:
   ```bash
   python3 -c "
   import json
   with open('artifacts/grade_results/results_<new_ts>.json') as f:
       data = json.load(f)
   for i, case in enumerate(data['eval_case_results']):
       r = case['response_candidate_results'][0]
       tq = r['metric_results'].get('multi_turn_tool_use_quality_v1', {})
       print(f'Case {i}: tool_use_quality={tq.get(\"score\")}')
       for v in (tq.get('rubric_verdicts') or []):
           desc = v['evaluated_rubric']['content']['property']['description'][:80]
           print(f'  [{\"PASS\" if v[\"verdict\"] else \"FAIL\"}] {desc}')
   "
   ```

5. If any metric regressed relative to baseline, identify which rubric(s) newly failed and
   diagnose whether the regression is from Phase 1 (dataset), Phase 2 (instruction), or
   Phase 3 (tool_config). Roll back the offending phase change and iterate.

6. If `tool_use_quality` is still 0 after Phase 3 changes, check whether `mode=ANY` triggered
   the fallback scenario described in Phase 3 (agent calling `scope_analyzer` on approval turn).
   If so, implement the `before_model_callback` approach from Phase 3's fallback section.

## Success Criteria

- [ ] `python3 -m json.tool tests/eval/datasets/full-pipeline-dataset.json` exits 0.
- [ ] `agents-cli eval run` completes without errors.
- [ ] `multi_turn_tool_use_quality_v1` mean score > 0.000.
- [ ] `final_response_quality_v1` mean score > 0.000.
- [ ] `multi_turn_task_success_v1` mean score >= 0.267.
- [ ] `custom_audit_plan_quality` mean score >= 4.500.
- [ ] `agents-cli eval compare` shows no regressions on any metric.
- [ ] Per-case rubric for `scope_analyzer` called shows PASS in at least one case.

## Risk Assessment

- If only Phase 1 (dataset fix) is done and Phases 2+3 are skipped, `tool_use_quality` may
  pass on the pre-seeded turn but the agent's fresh-run behavior remains broken. Both layers
  (dataset + agent fix) are needed for the eval to reflect real behavior.
- Eval grading uses a cloud LLM judge — scores have slight non-determinism (~±0.05). Run twice
  if borderline; use `judge_model_sampling_count: 3` in `eval_config.yaml` for stable scores.
