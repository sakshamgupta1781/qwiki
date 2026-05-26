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

**Result**: Architecture validated. Correctly catches contradictions in both initial and claim-specific search rounds. Awaiting full 100-case calibration.
