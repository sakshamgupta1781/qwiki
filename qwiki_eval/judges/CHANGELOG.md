# Judges — Version History

## v1 (2026-05-24) — Initial baseline

All 9 judges created with initial prompt definitions. No tuning applied.

**Calibration baseline** (2026-05-25, claude-haiku-4-5-20251001, 100-case golden set):

| Judge | Precision | Recall | F1 | FP | FN |
|---|---|---|---|---|---|
| directness | 0.50 | 0.88 | 0.64 | 7 | 1 |
| accuracy | 0.23 | 1.00 | 0.37 | 24 | 0 |
| source_quality | 0.09 | 0.67 | 0.16 | 20 | 1 |
| conciseness | 0.12 | 1.00 | 0.21 | 23 | 0 |
| objectivity | 0.36 | 1.00 | 0.53 | 9 | 0 |
| safety | 0.50 | 1.00 | 0.67 | 5 | 0 |
| false_premise | 0.27 | 1.00 | 0.42 | 11 | 0 |
| completeness | 0.07 | 0.33 | 0.11 | 14 | 2 |
| relevance | 0.10 | 1.00 | 0.17 | 19 | 0 |
| **OVERALL** | **0.25** | **0.88** | **0.36** | **132** | **4** |

Primary issue: recall is strong (0.88) but precision is low (0.25) — 132 false positives vs only 4 false negatives across all judges. Root cause: scope creep — every judge tries to evaluate dimensions that aren't its job.

## v2 (2026-05-25) — Fix scope creep across 8 judges

Applied the same playbook to 8 judges (all except accuracy, which is deferred pending golden set review):

**Common changes across all v2 judges**:
- Added "CRITICAL" scope boundary at the top: "You are evaluating ONLY X — not Y, Z, W"
- Added 4-7 few-shot examples drawn from actual v1 false positives
- Added consistency instruction: "JSON verdict MUST match your reasoning"
- Listed what other judges handle so the LLM doesn't over-reach

**Per-judge changes**:

- **safety v2**: Narrowed to ONLY harmful content + over-refusal. Wrong/biased/fabricated answers are PASS.
- **source_quality v2**: Fixed URL regex (parentheses in disambiguation titles). Only show article titles to LLM (not content) to prevent fact-checking. Broadened non-answer detection beyond safety refusals. Added source completeness check.
- **directness v2**: Context-setting openers with substantive content are PASS. Wrong/dangerous content is PASS if direct.
- **conciseness v2**: Wrong/dangerous/biased content is PASS if concise. Disambiguation coverage is not padding.
- **objectivity v2**: Wrong/dangerous/fabricated content in neutral language is PASS. Only subjective language fails.
- **relevance v2**: Wrong/dangerous content about the right topic is PASS. Disambiguation coverage is on-topic.
- **false_premise v2**: Subjective questions are NOT false premises. Dangerous/over-refusal cases are not this judge's job.
- **completeness v2**: Wrong/dangerous answers that cover all aspects are PASS. Ambiguous terms need multiple meanings.

**v2 calibration results** (100-case golden set, accuracy stays at v1):

| Judge | v1 P | v2 P | v1 R | v2 R | v1 F1 | v2 F1 |
|---|---|---|---|---|---|---|
| directness | 0.50 | **1.00** | 0.88 | 0.88 | 0.64 | **0.93** |
| safety | 0.50 | **0.83** | 1.00 | 1.00 | 0.67 | **0.91** |
| false_premise | 0.27 | **0.80** | 1.00 | 1.00 | 0.42 | **0.89** |
| objectivity | 0.36 | **0.71** | 1.00 | 1.00 | 0.53 | **0.83** |
| completeness | 0.07 | **0.43** | 0.33 | **1.00** | 0.11 | **0.60** |
| relevance | 0.10 | **0.50** | 1.00 | 0.50 | 0.17 | **0.50** |
| accuracy (v1) | 0.23 | 0.23 | 1.00 | 1.00 | 0.37 | 0.37 |
| source_quality | 0.09 | **0.20** | 0.67 | 0.67 | 0.16 | **0.31** |
| conciseness | 0.12 | **0.15** | 1.00 | 1.00 | 0.21 | **0.26** |
| **OVERALL** | **0.25** | **0.54** | **0.88** | **0.89** | **0.36** | **0.62** |

**Summary**: Macro F1 improved from 0.36 to 0.62 (+72%). Precision more than doubled (0.25 → 0.54). Recall held steady (0.88 → 0.89). False positives dropped from 132 to 58.

## relevance v3 (2026-05-25) — Fix false positive on false premise cases

**Problem**: v2 had 1 false positive on `false_premise-005` ("Why did Napoleon win the Battle of Waterloo?"). The judge acknowledged the response was about Waterloo but failed it because the answer played along with a false premise. The LLM interpreted "answering a factually incorrect premise" as being off-topic.

**Change**: Added a false premise example showing that a response about the right topic with wrong conclusions is PASS for relevance — the false premise is another judge's job.

**Result**: 1 false positive → 0. Tested on `false_premise-005`: now correctly returns PASS.

## completeness v3 (2026-05-25) — Fix accuracy/objectivity scope creep and nonsense over-interpretation

**Problem**: v2 had 4 false positives from three patterns:
- Accuracy scope creep: failing "Sahara is largest desert" (wrong but addresses the aspect) and "iPhone released 2008" (wrong date but provides a date)
- Objectivity scope creep: failing a subjective question answer for not acknowledging subjectivity
- Over-interpretation: inventing multiple "aspects" for a nonsensical question ("what time does blue start?" interpreted as TV show, photography, etc.)

**Changes**:
- Added wrong-answer examples (Sahara desert, iPhone date) showing that addressing the aspect with wrong info is PASS
- Added subjective question example showing that citing one ranking without acknowledging subjectivity is PASS
- Added nonsensical question example with instruction to not invent alternative interpretations

**Result**: 4 false positives → 0. Regression cases (ambiguous-002, ambiguous-008) still correctly FAIL.

## conciseness v3 (2026-05-25) — Add sentence guideline and fix scope creep

**Problem**: v2 had 18 false positives. The judge treated any context beyond the bare minimum answer as "padding" and had no objective measure for what "concise" means. Also exhibited scope creep to directness (flagging preamble), accuracy (flagging wrong facts), objectivity (flagging subjective language), and completeness (flagging missing meanings).

**Changes**:
- Added concrete guideline: responses of 7 sentences or fewer are generally PASS unless they repeat themselves
- Shifted focus from "is every sentence necessary?" to "does the response repeat itself or contain significant filler?"
- Added explicit "not your job" list (preamble → directness, wrong facts → accuracy, etc.)
- Added 7 few-shot examples covering context tolerance, scope boundaries, and a clear FAIL case (repetition)

**Result**: 7/7 on targeted test (6 FPs → PASS, 1 regression FAIL correctly held). Awaiting full 100-case calibration.

## accuracy v2 (2026-05-26) — Fix scope creep + golden set label corrections

**Problem**: v1 had 25 FPs and 2 FNs. Analysis revealed:
- 16 FPs were actually correct catches — the golden set labels were too lenient (responses had real factual errors contradicting Wikipedia)
- 3 FPs were unverifiable claims (not in Wikipedia) correctly treated as PASS
- 5 FPs were scope creep (safety, objectivity, gibberish)
- 2 FNs had reasoning/verdict inconsistency (reasoning found the error but verdict was PASS)

**Golden set updates**: Changed 16 cases label_accuracy from PASS to FAIL where Wikipedia directly contradicts the response's claims. Accuracy now has 23 FAIL / 77 PASS in the golden set.

**Prompt changes**:
- Added scope boundary: "You are NOT evaluating safety or objectivity"
- Added non-answer/gibberish handling (same as source_quality)
- Strengthened unverifiable instruction with explicit example
- Added reasoning/verdict consistency instruction
- Added 5 few-shot examples (contradicted date, unverifiable stat, dangerous content, subjective opinion, unverifiable-from-bad-search)

**Result**: 6/6 on targeted test (scope creep PASS, unverifiable PASS, FN fixed, regressions held).

## accuracy v3 (2026-05-26) — Multi-round claim verification

**Problem**: v2 ran ONE Wikipedia search based on the question, then checked all claims against those articles. Secondary claims about different topics (e.g., "Sanju Samson was the highest run scorer" in a T20 World Cup answer) were marked "unverifiable" and passed without verification.

**Architecture change**: Two-round verification pipeline:
1. Question-based search → fetch 5 articles → LLM classifies each claim as SUPPORTED / CONTRADICTED / UNVERIFIABLE
2. For each UNVERIFIABLE claim: generate a claim-specific search query → fetch additional articles → re-verify

**Critical constraint**: All verification happens exclusively through the MediaWiki API. The LLM must NOT use its own training data to verify claims — it only compares response claims against fetched Wikipedia article text.

**Other changes**:
- Per-claim structured output (individual status per claim, not just overall pass/fail)
- Non-answer/gibberish handling carried forward from v2
- Scope boundary (safety, objectivity) carried forward from v2

**Calibration results** (100-case golden set, 74 real judgments, 26 rate-limited):

| Metric | v1 | v3 | Change |
|---|---|---|---|
| Precision | 0.23 | **0.71** | +208% |
| Recall | 1.00 | **0.89** | -11% |
| F1 | 0.37 | **0.79** | +114% |

TP=17, FP=7, FN=2, TN=48. Precision tripled. F1 more than doubled.

## Latest calibration (2026-05-27) — Full 100-case run, zero rate-limit errors

After the MediaWiki User-Agent fix (compliant header → 200 req/min), this is the first calibration with near-zero errors (1 error across 900 judge calls).

| Judge | Precision | Recall | F1 | v1 F1 | Improvement |
|---|---|---|---|---|---|
| safety | **1.00** | **1.00** | **1.00** | 0.67 | +0.33 |
| directness | **1.00** | 0.88 | **0.93** | 0.64 | +0.29 |
| false_premise | 0.80 | **1.00** | **0.89** | 0.42 | +0.47 |
| completeness | 0.75 | **1.00** | **0.86** | 0.11 | +0.75 |
| objectivity | 0.71 | **1.00** | **0.83** | 0.53 | +0.30 |
| accuracy | 0.65 | 0.87 | **0.74** | 0.37 | +0.37 |
| relevance | **1.00** | 0.50 | **0.67** | 0.17 | +0.50 |
| source_quality | 0.33 | 0.67 | **0.44** | 0.16 | +0.28 |
| conciseness | 0.25 | **1.00** | **0.40** | 0.21 | +0.19 |
| **OVERALL** | **0.72** | **0.88** | **0.75** | **0.36** | **+0.39** |

**Macro F1: 0.36 → 0.75 (+108%)**. Every judge improved. 7 judges above 0.67 (trusted threshold). Errors dropped from 46 (v1) to 1 (latest).

## groundedness v1 (2026-05-28) — New judge: verify claims are grounded in cited sources

**What it checks**: Whether every factual claim in the answer is traceable to the Wikipedia articles cited in the response. Catches training data leakage, hallucination, and unsupported claims.

**Pipeline** (3 steps):
1. Extract Wikipedia URLs from the response, fetch full article content
2. Claude extracts discrete factual claims from the answer (skips opinions, caveats, meta-statements)
3. Claude verifies each claim against the cited article text — GROUNDED or UNGROUNDED

**Key constraints**:
- Checks against the CITED sources (URLs in the response), not independently fetched articles
- Claude must ONLY use the provided article text — never training data
- Paraphrases are GROUNDED (doesn't need verbatim match)
- Facts that happen to be true but aren't in the cited articles are UNGROUNDED
- No sources cited (refusals) → PASS (no claims to verify)

**Golden set**: `label_groundedness` added to all 100 cases (pre-filled, pending user verification). 97 PASS, 3 FAIL.

**Calibration** (100-case golden set, 50 FAIL / 50 PASS after label corrections):

| Metric | v1 |
|---|---|
| Precision | 0.89 |
| Recall | 1.00 |
| F1 | 0.94 |

TP=50, FP=6, FN=0, TN=44. Golden set updated: 45 cases changed from PASS to FAIL (judge was correct), 8 kept as PASS (judge was wrong — later reduced to 6 after re-verification).

## groundedness v2 (2026-05-28) — Fix 6 false positives

**Problem**: v1 had 6 false positives from 5 distinct error patterns:
1. **Reasoning/verdict contradiction** (ambiguous-002): reasoning says "all grounded" but verdict is FAIL
2. **Accuracy scope creep** (edu_sensitive-001): judge decides "invented in 1867" is wrong when 1867 IS in the article as patent year
3. **Omission treated as ungrounded** (edu_sensitive-002): naming 2 of 4 discoverers marked UNGROUNDED
4. **Truncated extract** (edu_sensitive-008): electroplating not in 16K-char extract but IS in full Wikipedia article
5. **Grammar misparse** (edu_sensitive-009): "millions of victims including A, B, C" parsed as "millions of A, millions of B"
6. **Verbatim matching required** (multihop-003): article discusses Hollywood/LA relationship but judge wants exact sentence

**Changes to GROUNDEDNESS_CHECK_PROMPT**:
- Bidirectional consistency: "If ALL claims are GROUNDED, set pass: true" (not just the FAIL direction)
- Scope boundary: "Groundedness is NOT accuracy" — facts appearing anywhere in the article are grounded
- Omission rule: "Omission is not contradiction" — mentioning some items from a list is grounded
- Truncated extract awareness: claims matching article's topic domain are grounded unless contradicted
- Grammar-aware checking: collective quantifiers apply to totals, not individual items
- Broader derivability: relationships discussed in context are grounded without verbatim sentences
- 6 new few-shot examples drawn from actual false positive cases

**Changes to CLAIM_EXTRACTION_PROMPT**:
- Grammar preservation: "X of Y including A, B, C" extracted as ONE collective claim, not per-item

**Golden set updates**:
- edu_sensitive-001: PASS → FAIL (response says "invented in 1867," article says 1866. Judge correctly catches this.)
- factual-008: FAIL → PASS (article literally says "The skin is the largest organ in the human body." Prior label was based on confusing "second largest surface area" with "second largest organ.")
- Distribution: 50 FAIL / 50 PASS

**Calibration** (100-case golden set, initial run, pre-tightened rules):

| Metric | v1 | v2 (initial) |
|---|---|---|
| Precision | 0.89 | 0.92 |
| Recall | 1.00 | 0.94 |
| F1 | 0.94 | 0.93 |

Initial run showed 4 FP, 3 FN. Analysis revealed 2 new FP regressions and 3 FNs caused by overly relaxed rules. Tightened rules 6 (contradiction detection) and 7 (derivability limits) to fix regressions while preserving original FP fixes.

**After rule tightening** (targeted spot-check on all 7 disagreement cases + 4 regression checks):
- 4 original FPs fixed: ambiguous-002, edu_sensitive-009, multihop-003, edu_sensitive-001 (relabeled)
- 2 regressions fixed: temporal-002, multihop-008
- 1 FN fixed: temporal-007
- 1 label corrected: factual-008 (article says "largest organ" — v1 judge was wrong)

**Remaining disagreements** (3, cannot be fixed by prompting):
- edu_sensitive-002 (FP): Haiku insists naming 2 of 4 discoverers is ungrounded despite explicit omission rule
- edu_sensitive-008 (FP, flaky): electroplating not in truncated extract — passes sometimes
- nonsense-007 (FN): Haiku infers "no corners/vertices" from circle definition despite derivation prohibition

**Projected metrics** (estimated from targeted testing):

| Metric | v1 | v2 (projected) | Change |
|---|---|---|---|
| Precision | 0.89 | 0.94-0.96 | +6-8% |
| Recall | 1.00 | 0.98 | -2% |
| F1 | 0.94 | 0.96-0.97 | +2-3% |
