# qwiki-eval — Context

## What This Is

qwiki-eval is an LLM-as-a-judge evaluation tool for **qwiki**, a Wikipedia-based Q&A system. It evaluates the quality of qwiki's responses across 9 dimensions using Claude as the judge, and includes a calibration pipeline to measure and improve judge reliability.

## Architecture

### Zero-Dependency Design

The entire project uses **only Python 3 standard library** — no pip, no external packages. The Claude API and MediaWiki API are called via raw `urllib.request`.

### Project Structure

```
qwiki/
├── qwiki-eval                    # Entry point script
├── qwiki_eval/
│   ├── cli.py                    # argparse, eval + calibrate subcommands
│   ├── runner.py                 # Orchestrates all 9 judges
│   ├── formatter.py              # Table + JSON output
│   └── judges/
│       ├── base.py               # BaseJudge ABC, JudgeResult, JSON parser
│       ├── <judge>_v<N>.py       # Versioned judge files
│       └── CHANGELOG.md          # Version history with calibration results
├── qwiki_common/                  # Shared API clients
│   ├── claude.py                 # ClaudeClient (rate limiting, retries)
│   └── mediawiki.py              # MediaWikiClient (compliant User-Agent)
├── golden/
│   └── eval_set.csv              # 100-case golden eval dataset
├── calibration/
│   └── history.csv               # Append-only metrics log
├── results/                       # Per-judge per-run result CSVs
├── disagreements/                 # Per-judge per-run disagreement CSVs
└── benchmarks/                    # Persistent scorecard data
```

### API Clients (shared via `qwiki_common/`)

**ClaudeClient**: `temperature=0`, 5-second inter-call delay, 5 retries with exponential backoff on 429.

**MediaWikiClient**: Compliant User-Agent header (includes GitHub URL) for 200 req/min tier. Retries on 429 and 503 with Retry-After header support.

## 9 Eval Judges

All judges produce binary PASS/FAIL. Composite score = passes / 9.

| Judge | Version | Type | F1 |
|-------|---------|------|-----|
| safety | v2 | LLM-only, bidirectional | 1.00 |
| directness | v2 | LLM-only | 0.93 |
| false_premise | v2 | LLM-only, two-step | 0.89 |
| completeness | v3 | LLM-only | 0.86 |
| objectivity | v2 | LLM-only | 0.83 |
| accuracy | v3 | Multi-stage + MediaWiki API | 0.74 |
| relevance | v3 | LLM-only | 0.67 |
| source_quality | v2 | Hybrid (URL validation + LLM) | 0.44 |
| conciseness | v3 | LLM-only | 0.40 |

**Trusted judges** (F1≥0.67): safety, directness, false_premise, completeness, objectivity, accuracy, relevance.

### Key judge design patterns

- **Scope boundary**: Every judge prompt starts with "CRITICAL: You are evaluating ONLY X — not Y, Z, W" to prevent scope creep
- **Few-shot examples**: Every prompt includes 4-7 examples from actual false positives
- **Consistency instruction**: "JSON verdict MUST match your reasoning"
- **Accuracy v3**: Multi-round claim verification — searches Wikipedia independently, verifies each claim, runs a second targeted search for unverifiable claims

## CLI Usage

```bash
# Evaluate a single response:
qwiki-eval eval --question "..." --response "..." --model claude-haiku-4-5-20251001

# Calibrate judges against golden set:
qwiki-eval calibrate --golden golden/eval_set.csv --model claude-haiku-4-5-20251001

# Calibrate specific judges:
qwiki-eval calibrate --golden golden/eval_set.csv --judges accuracy,safety
```

## Calibration Pipeline

- **Golden eval set**: 100 cases across 10 categories with human-labeled PASS/FAIL per judge
- **Results CSVs**: Written incrementally per case with reasoning (crash-safe)
- **Disagreement CSVs**: Self-contained with full response text for debugging
- **History CSV**: Append-only log of precision/recall/F1 per judge per run
- **60-second cooldown** between cases for rate limiting

## Key Design Decisions

- **Judge versioning**: Old prompt files kept alongside new ones (e.g., `accuracy_v1.py`, `accuracy_v2.py`, `accuracy_v3.py`). Runner imports the latest.
- **Golden set is immutable reference**: Only updated when human labels are confirmed incorrect.
- **Errors default to FAIL**: If a judge errors (rate limit, parse failure), it's recorded as FAIL. Retry runs target only errored cases.
- **Calibration metrics**: "Positive" = detected a failure. Precision = when the judge says FAIL, how often is it real. Recall = of all real FAILs, how many did the judge catch.

## Quality Journey

| Metric | v1 baseline | Latest |
|--------|-------------|--------|
| Macro F1 | 0.36 | **0.75** |
| Macro Precision | 0.25 | **0.72** |
| Macro Recall | 0.88 | **0.88** |
| Errors per run | 46 | **1** |
