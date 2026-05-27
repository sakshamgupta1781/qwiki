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

### Test results (50-case suite, 41 answered, 5 refused)

| Metric | v1 | v2 | Change |
|---|---|---|---|
| Trusted (7 judges) | 98.0% | 98.1% | +0.1% |
| Composite (all 9) | 89.8% | 88.9% | -0.8% |

**Per-category trusted scores**:
- factual_numeric: 97.1% → **100.0%** (+2.9%)
- ambiguous: 88.6% → **87.1%** (-1.4%) — not improved
- All other categories: unchanged at 100%

**Key finding**: The ambiguity detection fires correctly but doesn't improve results because the initial Wikipedia search already fills 5 article slots with one meaning (e.g., all Python programming language articles). The multi-search for other meanings fetches articles, but the synthesis prompt doesn't receive enough diverse content because the initial search dominates.

**Completeness failures**: 4 in v1 → 4 in v2 (am-001, am-002, am-003, am-005 still fail). Only am-004 ("Mercury") passes because Wikipedia's disambiguation naturally returns varied articles.

**Next steps for v3**: The search pipeline needs to LIMIT initial results to 2-3 articles, reserving slots for ambiguity search results. Or restructure to search per-meaning from the start when ambiguity is detected.
