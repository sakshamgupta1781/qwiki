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

**Next steps for v3**: The search pipeline needs to detect ambiguity BEFORE the initial search and allocate article slots per-meaning from the start.
