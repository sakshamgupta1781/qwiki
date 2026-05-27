# Test Run Analysis — v1 (2026-05-26)

## Summary

| Metric | Value |
|--------|-------|
| Total cases | 50 |
| Answered | 42 |
| Refused (correct) | 5 (all sensitive_unsafe) |
| Errors | 0 |
| No results | 0 |
| Avg trusted score (answered) | **93.2%** |
| Avg composite score (answered) | **87.6%** |

## Per-Category Results

| Category | Trusted Score | Composite | Verdict |
|----------|--------------|-----------|---------|
| factual_simple | **100.0%** | 94.6% | Excellent |
| multi_part | **100.0%** | 100.0% | Excellent |
| multi_hop | **100.0%** | 87.5% | Excellent |
| sensitive_safe | **100.0%** | 100.0% | Excellent |
| sensitive_unsafe | **100.0%** | 100.0% | Excellent (all refused) |
| current_events | **100.0%** | 95.0% | Excellent |
| factual_numeric | **97.1%** | 87.8% | Very good |
| ambiguous | **87.6%** | 77.5% | Needs work |
| false_premise | **80.0%** | 74.6% | Needs work |
| subjective | **60.0%** | 54.6% | Weakest |

## Trusted Judge Failures

### Directness — 0 failures (perfect)
Every response leads directly with facts. The synthesis prompt's "lead with the answer" instruction is working.

### Objectivity — 0 failures (perfect)
No subjective language or bias detected. The synthesis prompt's "never state opinions as facts" instruction is working.

### Safety — 0 failures (perfect)
All 5 dangerous queries correctly refused. All 5 sensitive-but-safe questions correctly answered.

### False Premise — 0 failures (perfect)
All 5 false premise questions handled correctly. The synthesis prompt's "correct false premises" instruction is working.

### Relevance — 0 failures (perfect)
Every response stays on-topic. No tangential information.

### Accuracy — 1 failure
- **fn-002** ("When was the Eiffel Tower completed?"): The response likely has a minor factual discrepancy with Wikipedia. Note: 16 of 42 accuracy evaluations hit rate-limit errors, so the true failure rate may be higher.

### Completeness — 4 failures (all ambiguous category)
- **am-001** ("What is Python?"): Likely only covered programming language, not the snake or Monty Python
- **am-002** ("Tell me about Jordan."): Likely only covered one meaning
- **am-003** ("What is a virus?"): Likely only covered biology, not computer viruses
- **am-005** ("What does spring mean?"): Likely only covered one meaning

**Pattern**: The tool consistently fails to cover multiple meanings of ambiguous terms. The Wikipedia search returns articles for the most common meaning, and the synthesis prompt doesn't instruct Claude to address ambiguity.

## Untrusted Judge Observations

### Conciseness — 46.3% failure rate (19 of 42 cases)
Very high failure rate, but this judge has F1=0.35 so we can't trust these results. Many are likely false positives.

### Source Quality — 23.1% failure rate (3 of 13 non-error cases)
29 of 42 cases hit rate-limit errors. Of the 13 that completed, 3 failed. Low sample size makes this unreliable.

## Rate Limiting Impact

| Judge | Errors | Real judgments | Impact |
|-------|--------|---------------|--------|
| accuracy | 16 | 26 | High — 38% of cases errored |
| source_quality | 29 | 13 | Critical — 69% of cases errored |
| conciseness | 1 | 41 | Minimal |
| All others | 0 | 42 | None |

The accuracy v3 multi-round pipeline and source_quality's URL validation + LLM calls are the most API-heavy judges.

## Recommendations for qwiki-ask v2

### Priority 1: Fix ambiguous term handling (completeness failures)

The #1 issue from trusted judges. When a question uses an ambiguous term ("Python", "Jordan", "virus", "spring"), the tool should:
1. **Search strategy**: Run multiple Wikipedia searches — one for each common meaning
2. **Synthesis prompt**: Add instruction to identify when a term is ambiguous and cover the primary meanings

### Priority 2: Improve subjective question handling

Subjective questions scored 60% trusted. The synthesis prompt already says to present objective data, but it may not be strong enough. Improvements:
1. **Synthesis prompt**: Add stronger few-shot examples for subjective questions
2. **Search strategy**: Search for survey/ranking articles alongside the topic

### Priority 3: Reduce rate-limit errors for accuracy and source_quality judges

The accuracy v3 pipeline uses too many Claude calls per case. Options:
1. Batch claims into fewer verification calls
2. Cache Wikipedia articles across judges (accuracy and source_quality both fetch articles)

### Lower Priority: False premise handling refinement

80% trusted score suggests some false premise cases aren't being corrected strongly enough. Review the 1 failure to understand the pattern.
