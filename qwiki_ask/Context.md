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

## Architecture

### 4-Phase Pipeline

```
Question → Safety Gate → Wikipedia Search → Synthesis → Output
```

**Phase 1: Safety Gate** (`safety.py`)
- Single Claude call classifies question as SAFE / UNSAFE / GIBBERISH
- UNSAFE: refusal message, exit
- GIBBERISH: "please rephrase" message, exit
- SAFE: proceed with optimized search query
- Fails open: if Claude errors, proceeds with the question

**Phase 2: Search** (`search.py`)
- Uses the search query from Phase 1 to search MediaWiki API (top 5 results)
- Fetches full article extracts (NO truncation)
- If zero results: tries a simplified query (first 3 words of question)
- Only errors if zero articles found after retry

**Phase 3: Synthesis** (`synthesize.py`)
- Claude answers using ONLY the Wikipedia article text provided
- Direct answer, no throat-clearing, 3-5 sentences
- Handles: false premises (corrects them), subjective questions (presents data), dangerous topics (educational only)
- Returns structured data: answer, sources, could_answer flag

**Phase 4: Output** (`formatter.py`)
- Unicode box-drawing formatted output to console
- Sections: Answer, Sources (article references), Links (Wikipedia URLs)
- Special formatters for refusals, gibberish, no results, and unanswerable questions

### Shared API Clients

`qwiki_common/claude.py` and `qwiki_common/mediawiki.py` are shared between qwiki-ask and qwiki-eval. The eval judges have their own verification logic but use the same underlying API clients.

## CLI Usage

```bash
# Basic:
qwiki-ask "Who discovered penicillin?"

# With specific model:
qwiki-ask --model claude-haiku-4-5-20251001 "What is the tallest building?"

# Debug mode (shows each pipeline phase):
qwiki-ask --debug "When was the Berlin Wall built?"
```

If `--model` is omitted, an interactive picker lists available Claude models.

## Design Decisions

- **Safety gate combined with query optimization**: A single Claude call handles both safety classification and search query generation, reducing API calls.
- **No article truncation**: Full Wikipedia articles are passed to Claude for synthesis. This uses more tokens but ensures no information is lost.
- **Fail-open safety**: If the safety gate Claude call fails, the question proceeds rather than blocking. This prioritizes availability over safety — the synthesis prompt has its own safety instructions as a backup.
- **Simplified query fallback**: If the optimized search query returns zero results, falls back to the first 3 words of the question before giving up.
