# qwiki-ask — Context

## What This Is

qwiki-ask is a command-line tool that answers questions using Wikipedia as the sole knowledge source. Claude is used under the hood for query optimization, safety checking, and answer synthesis — but all factual content comes exclusively from the MediaWiki API.

This is the tool that qwiki-eval was built to evaluate.

## Constraints

- Python 3 standard library only (no pip dependencies)
- `ANTHROPIC_API_KEY` environment variable required
- Wikipedia (MediaWiki API) is the ONLY source of truth — no built-in search, Perplexity, Google, or LLM training data for answers
- No truncation of Wikipedia articles — full content analyzed
- Every system prompt includes few-shot examples
- No prompt may divulge answers from Claude's training data

## Architecture

### Pipeline (v3 — current)

```
Question → Safety Gate → Query Optimization → Wikipedia Search
        → Ambiguity Detection → Synthesis → [Deep Search if needed] → Output
```

**Phase 1: Safety Gate** (`safety.py`)
- Single Claude call classifies question as SAFE / UNSAFE / GIBBERISH
- UNSAFE: refusal message, exit
- GIBBERISH: "please rephrase" message, exit
- SAFE: proceed
- Fails open: if Claude errors, proceeds with the question

**Phase 2: Search** (`search_v3.py`)
- Query optimization: Claude converts question to search-friendly terms using ONLY words from the question (no answer leaking)
- MediaWiki API search for top 5 results, full article extracts (NO truncation)
- Ambiguity detection: Claude checks if the term has multiple meanings, runs additional searches per meaning
- Fallback: tries simplified query if zero results

**Phase 3: Synthesis** (`synthesize_v3.py`)
- Claude answers using ONLY the fetched Wikipedia article text
- Direct answer, no throat-clearing, 3-5 sentences
- Never refuses when articles exist — shares what's available with caveats
- Time-sensitive: "I can't provide real-time data, but historically..."
- Predictions: "I can't predict, but here's the history..."
- Handles: false premises, subjective questions, ambiguous terms
- Sources field lists ONLY articles actually used (not all fetched)
- Post-processing strips any leaked metadata from the answer text

**Phase 3b: Deep Search** (`search_v3.py`, single-turn)
- Triggers when synthesis says `could_answer: false`
- Claude generates a refined search query based on what's missing
- ONE additional Wikipedia search + re-synthesis
- If second attempt also fails, accepts the failure
- Disabled with `--no-deep-search`

**Phase 4: Output** (`formatter.py`)
- Unicode box-drawing formatted output to console
- Links filtered to only show articles referenced in Sources
- Spinners with status bar showing pipeline progress
- Integrated eval judges run after answer (disable with `--no-eval`)

### Prompt Versioning

| Module | Current | Previous versions |
|--------|---------|-------------------|
| safety | safety.py | — |
| search | search_v3.py | search_v1.py, search_v2.py |
| synthesize | synthesize_v3.py | synthesize_v1.py, synthesize_v2.py |

### Shared API Clients

`qwiki_common/claude.py` and `qwiki_common/mediawiki.py` are shared between qwiki-ask and qwiki-eval. MediaWiki client uses a compliant User-Agent header (`qwiki/1.0` + GitHub URL) for 200 req/min rate limit tier.

## CLI Usage

```bash
# Standalone:
qwiki-ask "Who discovered penicillin?"
qwiki-ask --model claude-haiku-4-5-20251001 "What is Python?"
qwiki-ask --no-eval "Quick answer please"
qwiki-ask --no-deep-search "Simple question"
qwiki-ask --debug "Show pipeline details"

# Via the qwiki REPL:
qwiki> /ask Who discovered penicillin?
```

## Key Design Decisions

- **Query optimization must not leak answers**: The search query uses ONLY words from the question. "Who discovered penicillin?" → "penicillin discovery" (not "Alexander Fleming penicillin").
- **No article truncation**: Full Wikipedia articles passed to Claude. Uses more tokens but ensures no information is lost.
- **Deep search is single-turn**: If the second search attempt also fails, stop. No infinite retry loops.
- **Never refuse when articles exist**: Synthesis must share what's available, even if it doesn't fully answer the question. Only `could_answer: false` when zero articles.
- **Source filtering**: Links section only shows articles actually used for the answer, not all fetched articles.

## Quality Metrics (v3)

**Eval quality** (50-case test suite): Composite 92.6%, Trusted 98.0%
**Refusal rate** (50-case refusal suite): 1 incorrect refusal out of 35 answerable questions, 0 incorrect answers
