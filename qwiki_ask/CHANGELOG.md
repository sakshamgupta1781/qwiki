# qwiki-ask — Version History

## v1 (2026-05-26) — Initial release

First version of the qwiki-ask pipeline with 4 phases:
1. Safety gate (SAFE/UNSAFE/GIBBERISH classification)
2. Query optimization (question → search-friendly terms)
3. Wikipedia search + article fetch (up to 5 articles, no truncation)
4. Synthesis (Claude answers using ONLY Wikipedia content)

**Prompts**: `safety.py`, `search_v1.py` (query optimization), `synthesize_v1.py`

**Test results** (50-case test suite, 42 answered, 5 refused):

| Judge | Pass Rate | Trust |
|---|---|---|
| directness | 100.0% | ✓ |
| objectivity | 100.0% | ✓ |
| safety | 100.0% | ✓ |
| false_premise | 100.0% | ✓ |
| relevance | 100.0% | ✓ |
| accuracy | 95.0% | ✓ |
| completeness | 90.5% | ✓ |
| source_quality | 67.6% | |
| conciseness | 52.4% | |

**Composite: 89.5% | Trusted (7 judges): 97.9%**

**Weaknesses identified**:
- Ambiguous terms (88.6% category score): only covers one meaning of "Python", "Jordan", etc.
- Completeness: 4 failures, all in the ambiguous category
- Query optimization leaked answers from training data (fixed mid-v1)

## v2 (2026-05-26) — Ambiguous term handling + Subjective improvements

**Problem 1: Ambiguous terms** — v1 ran ONE Wikipedia search with ONE query. For "What is Python?", results only covered one meaning (usually the snake), missing the programming language and Monty Python entirely.

**Problem 2: Subjective questions** — v1's synthesis prompt said "present objective data" but didn't give strong enough examples. Responses sometimes leaned toward opinions.

### Search pipeline changes (`search_v2.py`)

- **Ambiguity detection**: After initial search, Claude checks if the question term has multiple well-known meanings
- **Multi-search**: For ambiguous terms, runs additional Wikipedia searches for each meaning (e.g., "Python programming language", "Python snake", "Monty Python")
- **Deduplication**: Merges articles across all searches, no duplicates
- **Constraints maintained**: No answer leaking, no web search, Wikipedia-only

### Synthesis prompt changes (`synthesize_v2.py`)

- **Ambiguous term instruction**: "If articles cover multiple meanings, address ALL primary meanings briefly. Don't assume the user means only one."
- **Stronger subjective handling**: Added explicit WRONG/RIGHT example pairs showing how to present surveys, rankings, and multiple candidates instead of opinions
- **All constraints maintained**: Wikipedia-only, no training data for answers, no web search

### Test results (50-case suite, 41 answered, 5 refused, 0 errors)

| Metric | v1 | v2 | Change |
|---|---|---|---|
| Trusted (7 judges) | 98.0% | 97.6% | -0.4% |
| Composite (all 9) | 89.8% | 88.1% | -1.7% |
| Errors | 7 | **0** | Fixed |

**Per-judge pass rates**:

| Judge | v1 | v2 | Trust |
|---|---|---|---|
| directness | 100.0% | 100.0% | ✓ |
| objectivity | 100.0% | 100.0% | ✓ |
| safety | 100.0% | 100.0% | ✓ |
| false_premise | 100.0% | 100.0% | ✓ |
| relevance | 100.0% | 100.0% | ✓ |
| accuracy | 95.0% | 92.7% | ✓ |
| completeness | 90.5% | 90.2% | ✓ |
| source_quality | 67.6% | 63.4% | |
| conciseness | 52.4% | 46.3% | |

**Per-category trusted scores**:
- ambiguous: 88.6% → 88.6% (unchanged)
- multi_part: 100.0% → 97.1% (-2.9%)
- All other categories: unchanged

**Key finding**: v2 is essentially flat vs v1 on trusted scores. The ambiguity detection fires correctly and fetches diverse articles (verified manually with "What is Python?" covering programming language, snake, Monty Python, and Cold War codename). However, the 50-case test suite shows no measurable improvement because the completeness judge still flags the same 4 ambiguous cases.

**Completeness failures**: 4 in v1 → 4 in v2 (am-001, am-002, am-003, am-005 still fail).

**Infrastructure win**: The MediaWiki User-Agent fix (compliant header → 200 req/min instead of 10 req/min) eliminated all Wikipedia rate limiting. v1 had 7 errors, v2 has 0 after retries.

### Refusal rate baseline (50-case refusal test suite)

| Metric | v2 |
|---|---|
| Total cases | 50 |
| Answered | 22 |
| Refused | 28 |
| Overall refusal rate | 56% |
| **Incorrect refusals** | **13/35** (37%) |
| Incorrect answers | 0/15 (perfect safety) |

Incorrect refusal root causes:
- Wrong articles fetched (6 cases): search query surfaces irrelevant articles
- Synthesis too strict (3 cases): articles have partial info but synthesis refuses
- Time-sensitive/prediction (4 cases): refuses instead of sharing historical data

## v3 (2026-05-27) — Deep search + synthesis never-refuse improvements

### Problem

v2 incorrectly refuses 13 of 35 answerable questions (37% incorrect refusal rate). All failures are `no_answer` — synthesis has articles but says "I can't answer."

### Search pipeline changes (`search_v3.py`)

- **Deep search mode**: When synthesis fails, a single retry step generates a refined Wikipedia search query and re-runs synthesis with expanded articles
- Single-turn only — if the second attempt also fails, accept the failure
- Deep search prompt uses ONLY question context for the refined query — no answer leaking, no web search, no training data
- Disabled with `--no-deep-search` flag

### Synthesis prompt changes (`synthesize_v3.py`)

- **Never refuse when articles exist**: `could_answer: false` is only for zero articles. When articles exist but don't fully answer, the tool must share what IS available with a caveat
- **Time-sensitive handling**: "I cannot provide real-time data, but according to Wikipedia, as of [date]..." instead of refusing
- **Prediction handling**: "I cannot predict the outcome, but based on Wikipedia, here is the history..." instead of refusing
- **Partial info**: "I wasn't able to find the exact answer, but based on the available articles..." instead of refusing
- All constraints maintained: Wikipedia-only, no training data, no web search

### Test results

Awaiting v3 refusal test run.
