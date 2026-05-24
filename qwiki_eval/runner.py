from .judges.directness import DirectnessJudge
from .judges.accuracy import AccuracyJudge
from .judges.source_quality import SourceQualityJudge
from .judges.conciseness import ConcisenessJudge
from .judges.objectivity import ObjectivityJudge
from .judges.safety import SafetyJudge
from .judges.false_premise import FalsePremiseJudge
from .judges.completeness import CompletenessJudge
from .judges.relevance import RelevanceJudge
from .judges.base import JudgeResult

ALL_JUDGES = [
    DirectnessJudge(),
    AccuracyJudge(),
    SourceQualityJudge(),
    ConcisenessJudge(),
    ObjectivityJudge(),
    SafetyJudge(),
    FalsePremiseJudge(),
    CompletenessJudge(),
    RelevanceJudge(),
]


def run_eval(question, response, claude_client, judge_names=None):
    judges = ALL_JUDGES
    if judge_names:
        judges = [j for j in ALL_JUDGES if j.name in judge_names]

    results = []
    for judge in judges:
        try:
            result = judge.evaluate(question, response, claude_client)
        except Exception as e:
            result = JudgeResult(
                judge_name=judge.name,
                passed=False,
                reasoning=f"ERROR: {e}",
            )
        results.append(result)

    passed = sum(1 for r in results if r.passed)
    composite = (passed / len(results) * 100) if results else 0.0

    return results, composite
