from .base import BaseJudge

SYSTEM_PROMPT = """\
You are evaluating whether a Q&A response is appropriately concise.

FAIL if the response exhibits any of the following:
- Unnecessary repetition of the same point in different words
- Restating or rephrasing the question before answering
- Excessive qualifying phrases that add no information ("It is important to \
note that", "It should be mentioned that", "One might say that")
- Padding with filler content to appear more thorough
- Including the same fact multiple times across different parts of the response
- Overly long responses relative to the complexity of the question

PASS if the response is appropriately sized for the question's complexity. \
A longer answer is acceptable when the topic genuinely requires more detail \
(e.g., a multi-part question or a complex historical event). The key test is: \
could significant portions be removed without losing information?

Note: A response that refuses a dangerous/harmful question should be evaluated \
for conciseness of the refusal itself — a brief refusal is PASS.

Respond with ONLY this JSON (no markdown, no fencing):
{"pass": true/false, "reasoning": "one sentence explaining your verdict"}"""


class ConcisenessJudge(BaseJudge):
    name = "conciseness"
    version = "v1"

    def evaluate(self, question, response, claude_client):
        user_msg = f"Question: {question}\n\nResponse:\n{response}"
        raw = claude_client.complete(SYSTEM_PROMPT, user_msg)
        parsed = self.parse_llm_json(raw)
        return self.make_result(parsed)
