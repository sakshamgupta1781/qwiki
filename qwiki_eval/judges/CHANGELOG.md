# Judges — Version History

## v1 (2026-05-24) — Initial baseline

All 9 judges created with initial prompt definitions. No tuning applied.

**Calibration baseline** (2026-05-25, claude-haiku-4-5-20251001, 100-case golden set, 5s inter-call delay + 60s cooldown between cases, zero 429 errors):

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

Primary issue: recall is strong (0.88) but precision is low (0.25) — 132 false positives vs only 4 false negatives across all judges.
