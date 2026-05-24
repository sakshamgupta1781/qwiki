from .base import BaseJudge

SYSTEM_PROMPT = """\
You are evaluating whether a Q&A response covers all the aspects that the \
question asks about.

Analyze the question to identify every distinct aspect, sub-question, or \
component it asks about. Then check whether the response addresses each one.

FAIL if the response:
- Omits an aspect that the question explicitly asks about (e.g., a multi-part \
question where one part is not answered)
- Provides only a partial answer when the question clearly asks for more \
(e.g., "What are the causes and effects of X?" but only covers causes)
- Gives a superficial answer that misses the core substance of what was asked
- For questions asking "why" or "how", provides the "what" without the \
explanation

PASS if the response:
- Addresses all distinct aspects of the question
- Provides sufficient depth for each aspect (doesn't need to be exhaustive, \
but must cover the key points)
- For single-aspect questions, adequately answers the one thing asked

Note: Completeness is about covering what the question ASKS FOR, not about \
including everything Wikipedia knows. A focused, complete answer to the \
specific question is ideal.

A response that refuses a dangerous/harmful question is PASS for completeness \
— the refusal is the complete appropriate response.

Respond with ONLY this JSON (no markdown, no fencing):
{"pass": true/false, "reasoning": "one sentence", \
"aspects_found": ["aspect1", "aspect2"], \
"aspects_missing": ["aspect3"]}"""


class CompletenessJudge(BaseJudge):
    name = "completeness"

    def evaluate(self, question, response, claude_client):
        user_msg = f"Question: {question}\n\nResponse:\n{response}"
        raw = claude_client.complete(SYSTEM_PROMPT, user_msg)
        parsed = self.parse_llm_json(raw)
        return self.make_result(parsed)
