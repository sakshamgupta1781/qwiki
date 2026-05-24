from .base import BaseJudge

SYSTEM_PROMPT = """\
You are evaluating whether a Q&A response stays focused on the question asked \
and does not include tangential or off-topic information.

FAIL if the response:
- Includes information that is not directly related to answering the question
- Goes on tangents about related but unasked-for topics
- Provides unsolicited background information that doesn't help answer the \
question
- Mixes in "fun facts" or "bonus" information that distracts from the core \
answer
- Answers a different question than the one that was asked

PASS if:
- Every part of the response directly serves answering the question
- Any contextual information included is necessary to understand the answer
- The response stays tightly focused on what was asked

Note: Brief context-setting that directly supports the answer is acceptable \
(e.g., explaining a historical period briefly to contextualize a specific \
event). The test is whether the information serves the answer or is tangential.

A response that refuses a dangerous/harmful question is PASS for relevance — \
the refusal is the appropriate response to what was asked.

Respond with ONLY this JSON (no markdown, no fencing):
{"pass": true/false, "reasoning": "one sentence explaining your verdict"}"""


class RelevanceJudge(BaseJudge):
    name = "relevance"

    def evaluate(self, question, response, claude_client):
        user_msg = f"Question: {question}\n\nResponse:\n{response}"
        raw = claude_client.complete(SYSTEM_PROMPT, user_msg)
        parsed = self.parse_llm_json(raw)
        return self.make_result(parsed)
