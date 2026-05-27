# Testing — Context

## What This Is

End-to-end testing framework for qwiki-ask. Runs 50 diverse test questions through the ask pipeline, evaluates each response with all 9 judges, and produces analysis to guide improvements.

## Trusted vs Untrusted Judges

Based on calibration F1 scores, we split judges into trusted (prioritize failures) and untrusted (note but don't act on):

**Trusted** (7 judges):
- safety (F1=1.00), directness (F1=0.93), completeness (F1=0.86)
- objectivity (F1=0.83), false_premise (F1=0.75), accuracy (F1=0.70)
- relevance (F1=0.67)

**Untrusted** (2 judges):
- source_quality (F1=0.57), conciseness (F1=0.35)

## Test Categories (50 cases, 5 per category)

| Category | Purpose |
|----------|---------|
| factual_simple | Basic single-fact lookups |
| factual_numeric | Numbers, dates, measurements |
| multi_part | Questions with multiple sub-questions |
| subjective | Opinion-seeking, needs objective framing |
| false_premise | Questions with incorrect assumptions |
| sensitive_safe | Educational questions on sensitive topics |
| sensitive_unsafe | Dangerous queries that should be refused |
| ambiguous | Terms with multiple meanings |
| multi_hop | Requires chaining facts across topics |
| current_events | Recent topics Wikipedia may/may not cover |

## Running Tests

```bash
python testing/run_tests.py --model claude-haiku-4-5-20251001
python testing/run_tests.py --model claude-haiku-4-5-20251001 --version v2
```

## Output Structure

Each run creates a timestamped directory:
```
testing/runs/v1_20260526_123456/
├── responses.csv      # qwiki-ask outputs + metadata
├── eval_results.csv   # per-judge PASS/FAIL + composite/trusted scores
└── analysis.md        # patterns, failure modes, recommendations
```

## Rate Limit Handling

- 60-second cooldown between test cases
- qwiki-ask failures retried up to 3 times with 60s backoff
- eval judge errors recorded as ERROR, retried after full run
- analysis only counts non-ERROR results for scores
