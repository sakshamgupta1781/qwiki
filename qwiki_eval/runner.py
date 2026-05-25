from .judges.directness_v1 import DirectnessJudge
from .judges.accuracy_v1 import AccuracyJudge
from .judges.source_quality_v1 import SourceQualityJudge
from .judges.conciseness_v1 import ConcisenessJudge
from .judges.objectivity_v1 import ObjectivityJudge
from .judges.safety_v1 import SafetyJudge
from .judges.false_premise_v1 import FalsePremiseJudge
from .judges.completeness_v1 import CompletenessJudge
from .judges.relevance_v1 import RelevanceJudge
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
