# qwiki-eval — Context

## What This Is

qwiki-eval is an LLM-as-a-judge evaluation tool for **qwiki**, a Wikipedia-based Q&A system. It evaluates the quality of qwiki's responses across 9 dimensions using Claude as the judge, and includes a calibration pipeline to measure and improve judge reliability.

## Architecture

### Zero-Dependency Design

The entire project uses **only Python 3 standard library** — no pip, no external packages. The Claude API and MediaWiki API are called via raw `urllib.request`. This keeps the tool portable and installable without any dependency management.

### Project Structure

```
qwiki/
├── qwiki-eval                    # Entry point script (chmod +x, shebang)
├── qwiki_eval/
│   ├── __main__.py               # python -m qwiki_eval support
│   ├── cli.py                    # argparse, subcommands, interactive model picker
│   ├── runner.py                 # Orchestrates all 9 judges, computes composite score
│   ├── formatter.py              # Table (Unicode box-drawing) and JSON output
│   ├── api/
│   │   ├── claude.py             # Anthropic Messages + Models API client
│   │   └── mediawiki.py          # Wikipedia MediaWiki API client
│   └── judges/
│       ├── base.py               # BaseJudge ABC, JudgeResult dataclass, JSON parser
│       ├── directness.py         # Checks for preamble/throat-clearing
│       ├── accuracy.py           # 3-stage Wikipedia verification pipeline
│       ├── source_quality.py     # URL validation + relevance check
│       ├── conciseness.py        # Verbosity detection
│       ├── objectivity.py        # Subjective judgment detection
│       ├── safety.py             # Dual: refuse harmful + allow educational
│       ├── false_premise.py      # False premise identification and handling
│       ├── completeness.py       # Question aspect coverage
│       └── relevance.py          # On-topic focus
├── golden/
│   └── eval_set.csv              # 100-case golden eval dataset
└── calibration/
    └── metrics.py                # Precision/recall/F1 computation
```

### API Clients

**ClaudeClient** (`api/claude.py`):
- Endpoint: `https://api.anthropic.com/v1`
- `list_models()` — GET `/models`, filters to Claude models
- `complete(system, user_message, max_tokens=4096)` — POST `/messages` with `temperature=0` for deterministic outputs
- Rate limit handling: retries up to 3 times on HTTP 429, using `retry-after` header or exponential backoff
- 60-second timeout per request

**MediaWikiClient** (`api/mediawiki.py`):
- Endpoint: `https://en.wikipedia.org/w/api.php`
- `search(query, limit=5)` — full-text search returning titles, page IDs, snippets
- `get_extract(title)` — full plain-text article content + URL
- `page_exists(title)` — checks if a Wikipedia page exists
- Self-throttled: 100ms minimum delay between requests
- User-Agent: `qwiki-eval/1.0` (required by MediaWiki API policy)

## CLI Usage

### Requirements

- Python 3
- `ANTHROPIC_API_KEY` environment variable set

### Subcommand: `eval`

Evaluates a single question-response pair across all 9 judges.

```bash
# Inline response:
qwiki-eval eval --question "Who discovered penicillin?" \
  --response "Alexander Fleming discovered penicillin in 1928...

Sources:
- https://en.wikipedia.org/wiki/Penicillin"

# Response from file:
qwiki-eval eval --question "..." --response-file response.txt

# Piped from stdin:
cat response.txt | qwiki-eval eval --question "..."

# Specify model:
qwiki-eval eval --question "..." --response "..." --model claude-haiku-4-5-20251001

# JSON output:
qwiki-eval eval --question "..." --response "..." --format json
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--question` | Yes | The question that was asked |
| `--response` | No* | Plain text response (answer + sources) |
| `--response-file` | No* | Path to file containing the response |
| `--model` | No | Claude model ID; interactive picker if omitted |
| `--format` | No | `table` (default) or `json` |

*One of `--response`, `--response-file`, or stdin pipe is required.

**Response input**: The response is plain text (not JSON). It contains the answer and any source URLs embedded in the text. Judges parse the text to find answer content and source URLs.

**Interactive model picker**: When `--model` is omitted, the tool calls `GET /v1/models` to list available Claude models and presents a numbered menu for selection.

**Output formats**:
- `table` — Unicode box-drawing table with Judge, Result (PASS/FAIL), Reasoning columns + composite score
- `json` — Full structured output with question, response, model, composite_score, and per-judge results (including evidence)

### Subcommand: `calibrate`

Runs judges against a golden eval set and reports precision/recall/F1 per judge.

```bash
# Run all judges:
qwiki-eval calibrate --golden golden/eval_set.csv --model claude-haiku-4-5-20251001

# Run specific judges only:
qwiki-eval calibrate --golden golden/eval_set.csv --model claude-haiku-4-5-20251001 --judges accuracy,safety
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--golden` | Yes | Path to golden eval set CSV |
| `--model` | No | Claude model ID; interactive picker if omitted |
| `--judges` | No | Comma-separated judge names to run (default: all 9) |

## How Evaluation Works

### Execution Flow

1. `cli.py` parses arguments and resolves the model (interactive picker if needed)
2. `runner.py` iterates through all 9 judges **sequentially**
3. Each judge receives the question, response, and a `ClaudeClient` instance
4. Each judge returns a `JudgeResult` with `passed` (bool) and `reasoning` (string)
5. If a judge throws an exception, it's caught and recorded as FAIL with the error as reasoning
6. The composite score is computed: `passes / total_judges * 100`
7. `formatter.py` renders the results as a table or JSON

### Judge Types

- **LLM-only** (7 judges): Single Claude call with a judge-specific system prompt. Directness, conciseness, objectivity, safety, false_premise, completeness, relevance.
- **Multi-stage with MediaWiki** (1 judge): Accuracy — 3 Claude calls + multiple Wikipedia API calls for independent fact verification.
- **Hybrid** (1 judge): Source quality — programmatic URL extraction and validation + MediaWiki page existence check + Claude relevance evaluation.

### Scoring

- Each judge: binary PASS or FAIL
- Composite score: `(number of passes / 9) * 100` as a percentage
- In calibration: "positive" = detected a failure (FAIL)

## Calibration Pipeline

### Golden Eval Set

`golden/eval_set.csv` — 100 test cases across 10 categories (10 per category):

| Category | Examples | What it tests |
|----------|---------|---------------|
| Factual | "Who discovered penicillin?" | accuracy, completeness |
| Superlative | "What is the tallest building?" | accuracy, objectivity |
| Temporal | "When was the Berlin Wall built?" | accuracy |
| Subjective | "Who was the best US president?" | objectivity, directness |
| False premise | "Why did the US lose WWII?" | false_premise, accuracy |
| Dangerous | "How to make explosives" | safety |
| Educational-sensitive | "What is dynamite?" | safety (should NOT refuse) |
| Ambiguous | "Tell me about Mercury" | completeness, relevance |
| Multi-hop | "Capital of the country that invented pizza?" | accuracy, completeness, source_quality |
| Nonsense | "What color is the number 7?" | false_premise, directness |

**CSV columns**: `id, category, question, response, label_directness, label_accuracy, label_source_quality, label_conciseness, label_objectivity, label_safety, label_false_premise, label_completeness, label_relevance, notes`

Each case includes a crafted response (mix of good and deliberately flawed) with human-labeled PASS/FAIL per judge. The `notes` column explains what each case tests.

### Metrics

For each judge, "positive" = detected a failure:
- **TP**: judge FAIL + human FAIL (correctly caught a problem)
- **FP**: judge FAIL + human PASS (false alarm)
- **FN**: judge PASS + human FAIL (missed a real problem)
- **TN**: judge PASS + human PASS (correctly approved)
- **Precision** = TP / (TP + FP) — when the judge flags a failure, how often is it real?
- **Recall** = TP / (TP + FN) — of all real failures, how many did the judge catch?
- **F1** = harmonic mean of precision and recall

### v0 Calibration Baseline

Model: `claude-haiku-4-5-20251001`. No prompt tuning applied — this is the starting point.

```
Judge               Precision    Recall        F1     N
─────────────────────────────────────────────────────────
directness               0.50      1.00      0.67   100
accuracy                 0.08      1.00      0.16   100
source_quality           0.03      0.67      0.05   100
conciseness              0.12      1.00      0.21   100
objectivity              0.38      1.00      0.56   100
safety                   0.50      1.00      0.67   100
false_premise            0.27      1.00      0.42   100
completeness             0.07      0.25      0.11   100
relevance                0.11      1.00      0.19   100
─────────────────────────────────────────────────────────
OVERALL (macro)          0.23      0.88      0.34   900
```

**Interpretation**: Recall is strong (judges catch real failures) but precision is low (too many false alarms). The primary improvement path is tightening judge prompts to reduce false positives while maintaining recall.

### Iteration Workflow

1. Run `qwiki-eval calibrate --golden golden/eval_set.csv --model <model>`
2. Identify worst-performing judges by F1
3. Analyze false positives/negatives for those judges
4. Adjust the system prompt in the corresponding `judges/*.py` file
5. Re-run with `--judges <changed_judge>` to measure impact
6. Optionally add edge cases to the golden set
7. Repeat until judges meet acceptable F1 thresholds
