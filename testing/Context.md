# Testing — Context

## What This Is

End-to-end testing framework for qwiki-ask. Two test suites measure different aspects of tool quality:

1. **Eval test suite** (50 cases): Runs qwiki-ask + all 9 eval judges to measure response quality
2. **Refusal test suite** (50 cases): Measures how often the tool incorrectly refuses answerable questions

## Test Suites

### Eval Test Suite (`test_cases.csv`, 50 cases)

10 categories × 5 questions: factual_simple, factual_numeric, multi_part, subjective, false_premise, sensitive_safe, sensitive_unsafe, ambiguous, multi_hop, current_events.

Runner: `testing/run_tests.py`

Outputs per run:
- `responses.csv` — qwiki-ask outputs + metadata
- `eval_results.csv` — per-judge PASS/FAIL + composite/trusted scores

### Refusal Test Suite (`refusal_test_cases.csv`, 50 cases)

8 categories: factual_indirect (5), educational_sensitive (5), time_sensitive (5), complex_phrasing (5), edge_cases (5), dangerous (5), harmful_intent (5), gibberish (5), borderline_safe (5), borderline_unanswerable (5).

Runner: `testing/run_refusal_tests.py`

Outputs per run:
- `responses.csv` — status, refusal reason, search query, article titles
- `diagnostics/<case_id>.json` — full diagnostic data (article content, synthesis response, explanations)

## Trusted vs Untrusted Judges

Based on calibration F1 scores:

**Trusted** (7 judges): safety (1.00), directness (0.93), false_premise (0.89), completeness (0.86), objectivity (0.83), accuracy (0.74), relevance (0.67)

**Untrusted** (2 judges): source_quality (0.44), conciseness (0.40)

## Quality Metrics (latest)

### Response Quality (v3)
- Composite: **92.6%** | Trusted: **98.0%**
- 5 judges at 100%: accuracy, objectivity, safety, false_premise, relevance

### Refusal Rate (v3-fixed)
- Incorrect refusals: **1/35** (was 13/35 in v2)
- Incorrect answers: **0/15** (perfect safety)

## Rate Limiting

- 60-second cooldown between eval test cases (9+ Claude calls per case)
- 10-second cooldown between refusal test cases (3-4 Claude calls per case)
- MediaWiki: compliant User-Agent for 200 req/min (was 10 req/min before fix)
- Claude: 5-second inter-call delay, 5 retries with exponential backoff

## Scorecard (`/scorecard`)

Persistent benchmarks dashboard in the qwiki REPL showing judge calibration, response quality, and refusal rate with deltas from previous runs. Data stored in `benchmarks/` directory.

## Key Design Decisions

- **Eval judges run by default with /ask**: Response quality is always visible. Disable with `--no-eval`.
- **Refusal diagnostics are per-case JSON files**: Full article content + synthesis response for every test case, enabling root cause analysis.
- **Retry strategy**: Failed eval judges are retried individually (not the whole suite). Failed ask pipeline retried up to 3 times.
- **Version tracking**: Each test run labeled with tool version (v1, v2, v3) for comparison across iterations.
