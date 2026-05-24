import abc
import json
import re
from dataclasses import dataclass, field


@dataclass
class JudgeResult:
    judge_name: str
    passed: bool
    reasoning: str
    evidence: list = field(default_factory=list)


class BaseJudge(abc.ABC):
    name: str = ""

    @abc.abstractmethod
    def evaluate(self, question, response, claude_client):
        ...

    def parse_llm_json(self, raw):
        raw = raw.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        passed = None
        raw_lower = raw.lower()
        if '"pass": true' in raw_lower or '"pass":true' in raw_lower:
            passed = True
        elif '"pass": false' in raw_lower or '"pass":false' in raw_lower:
            passed = False

        if passed is not None:
            return {"pass": passed, "reasoning": raw[:200]}

        raise ValueError(f"Could not parse judge response: {raw[:300]}")

    def make_result(self, parsed, evidence=None):
        return JudgeResult(
            judge_name=self.name,
            passed=parsed.get("pass", False),
            reasoning=parsed.get("reasoning", ""),
            evidence=evidence or [],
        )
